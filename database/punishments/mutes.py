import datetime
import typing
from typing import Literal
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

if typing.TYPE_CHECKING:
    from database.actions.general import Actions


@dataclass
class Mute:
    user: int
    type: Literal['voice', 'text', 'full']
    guild: int
    action: int
    start: datetime.datetime
    duration: float


class Mutes:
    def __init__(self, collection: MotorCollection, actions: 'Actions'):
        self._collection = collection
        self.actions = actions

    async def get(self, user: int) -> list[Mute]:
        return [Mute(**doc) async for doc in self._collection.find({'user': user})]

    async def give(
            self, *,
            user: int, guild: int, moderator: int, mute_type: Literal['voice', 'text', 'full'],
            duration: float, reason: str
    ):
        if await self._collection.count_documents({'user': user, 'type': mute_type, 'guild': guild}):
            raise ValueError('У пользователя уже есть мут на этом сервере')

        action = await self.actions.record(
            user, guild, moderator, f'mute_{mute_type}_give',
            duration=duration, reason=reason
        )

        await self._collection.insert_one({
            'user': user, 'type': mute_type, 'guild': guild, 'action': action,
            'start': datetime.datetime.now(datetime.UTC), 'duration': duration
        })
