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
class Ban:
    user: int
    type: Literal['global', 'local']
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


class Bans:
    def __init__(self, collection: MotorCollection, actions: 'Actions'):
        self._collection = collection
        self._actions = actions
        self._expiration_callback: Optional[Callable[[Ban], Awaitable[None]]] = None
        self.current: list[Ban] = []

    async def load(self):
        self.current = [Ban(**doc) async for doc in self._collection.find()]
        for ban in self.current:
            _ = asyncio.create_task(ban.wait(self._on_expiration))

    async def _on_expiration(self, ban: Ban):
        while not self._expiration_callback:
            await asyncio.sleep(0.1)

        if ban not in self.current:
            return

        await self._collection.delete_one({'_id': ban.id})
        self.current.remove(ban)

        await self._expiration_callback(ban)

    def set_callback(self, callback: Callable[[Ban], Awaitable[None]]):
        self._expiration_callback = callback

    async def get(self, user: int) -> list[Ban]:
        return [Ban(**doc) async for doc in self._collection.find({'user': user})]

    async def get_by_id(self, action_id: int) -> Ban:
        return Ban(**await self._collection.find_one({'action': action_id}))

    async def apply(self, action: 'Act') -> Ban:
        ban_type = action.type.split('_')[1]
        guild = action.guild
        user = action.user
        duration = action.duration

        ban = Ban(
            user=user, type=ban_type, guild=guild, action=action.id,
            start=datetime.datetime.now(datetime.UTC), duration=duration
        )

        insert_info = await self._collection.insert_one(ban.as_dict)
        ban._id = insert_info.inserted_id

        self.current.append(ban)
        _ = asyncio.create_task(ban.wait(self._on_expiration))

        return ban

    async def give(
            self, *,
            user: int, guild: int, moderator: int, ban_type: Literal['global', 'local'],
            duration: float, reason: str, auto_review: bool = False, counting: bool = True
    ) -> 'Act':
        if ban_type == 'global':
            if await self._collection.count_documents({'user': user, 'type': ban_type}):
                raise ValueError('У пользователя уже есть глобальный бан')
        elif await self._collection.count_documents({'user': user, 'type': ban_type, 'guild': guild}):
            raise ValueError('У пользователя уже есть бан на этом сервере')

        action = await self._actions.record(
            user, guild, moderator, f'ban_{ban_type}_give',
            duration=duration, reason=reason, auto_review=auto_review, counting=counting
        )
            
        return action

    async def remove(self, user: int, guild: int, moderator: int, ban_type: Literal['global', 'local']) -> 'Act':
        ban = await self._collection.find_one({'user': user, 'type': ban_type, 'guild': guild})
        if not ban:
            raise ValueError('У пользователя нет бана на этом сервере')

        action = await self._actions.record(
            user, guild, moderator, f'ban_{ban_type}_remove',
            counting=False, auto_review=True
        )

        await self._collection.delete_one({'_id': ban['_id']})
        self.current = [m for m in self.current if m.id != ban['_id']]
        return action
