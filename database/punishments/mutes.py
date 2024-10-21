import asyncio
import datetime
import typing

from typing import Literal, Awaitable, Callable, Optional
from dataclasses import dataclass, asdict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

if typing.TYPE_CHECKING:
    from database.actions.general import Actions
    from database.actions.action import Act


@dataclass
class Mute:
    user: int
    type: Literal['voice', 'text', 'full']
    guild: int
    action: int
    start: datetime.datetime
    duration: float
    _id: ObjectId = None

    @property
    def as_dict(self):
        data = asdict(self)
        data.pop('_id')
        return data

    @property
    def id(self):
        return self._id

    async def wait(self, callback):
        start_aware = self.start.replace(tzinfo=datetime.timezone.utc)
        end = start_aware + datetime.timedelta(seconds=self.duration)
        now = datetime.datetime.now(datetime.timezone.utc)

        wait_duration = (end - now).total_seconds()
        if wait_duration > 0:
            await asyncio.sleep((end - now).total_seconds())

        await callback(self)


class Mutes:
    def __init__(self, collection: MotorCollection, actions: 'Actions'):
        self._collection = collection
        self._actions = actions
        self._expiration_callback: Optional[Callable[[Mute], Awaitable[None]]] = None
        self.current: list[Mute] = []

    async def load(self):
        self.current = [Mute(**doc) async for doc in self._collection.find()]
        for mute in self.current:
            _ = asyncio.create_task(mute.wait(self._on_expiration))

    async def _on_expiration(self, mute: Mute):
        while not self._expiration_callback:
            await asyncio.sleep(0.1)

        if mute not in self.current:
            return

        await self._collection.delete_one({'_id': mute.id})
        self.current.remove(mute)

        await self._expiration_callback(mute)

    def set_callback(self, callback: Callable[[Mute], Awaitable[None]]):
        self._expiration_callback = callback

    async def get(self, user: int) -> list[Mute]:
        return [Mute(**doc) async for doc in self._collection.find({'user': user})]

    async def give(
        self, *,
        user: int, guild: int, moderator: int, mute_type: Literal['voice', 'text', 'full'],
        duration: float, reason: str
    ) -> tuple['Act', Mute]:
        if await self._collection.count_documents({'user': user, 'type': mute_type, 'guild': guild}):
            raise ValueError('У пользователя уже есть мут на этом сервере')

        action = await self._actions.record(
            user, guild, moderator, f'mute_{mute_type}_give',
            duration=duration, reason=reason
        )

        mute = Mute(
            user=user, type=mute_type, guild=guild, action=action.id,
            start=datetime.datetime.now(datetime.UTC), duration=duration
        )

        insert_info = await self._collection.insert_one(mute.as_dict)
        mute._id = insert_info.inserted_id

        self.current.append(mute)
        _ = asyncio.create_task(mute.wait(self._on_expiration))
        
        return action, mute

    async def remove(self, user: int, guild: int, moderator: int, mute_type: Literal['voice', 'text', 'full'], auto_review: bool = False) -> 'Act':
        mute = await self._collection.find_one({'user': user, 'type': mute_type, 'guild': guild})
        if not mute:
            raise ValueError('У пользователя нет мута на этом сервере')

        action = await self._actions.record(
            user, guild, moderator, f'mute_{mute_type}_remove',
            counting=False, auto_review=auto_review or mute.get('moderator') == moderator
        )

        await self._collection.delete_one({'_id': mute['_id']})
        self.current = [m for m in self.current if m.id != mute['_id']]
        return action
    