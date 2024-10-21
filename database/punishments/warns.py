import typing

from dataclasses import dataclass, asdict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

if typing.TYPE_CHECKING:
    from database.actions.general import Actions
    from database.actions.action import Act


@dataclass
class WarnInfo:
    user: int
    guild: int
    count: int
    _id: ObjectId = None

    @property
    def as_dict(self):
        data = asdict(self)
        data.pop('_id')
        return data

    @property
    def id(self):
        return self._id


class Warns:
    def __init__(self, collection: MotorCollection, actions: 'Actions'):
        self._collection = collection
        self._actions = actions

    async def get(self, user: int) -> list[WarnInfo]:
        return [WarnInfo(**doc) async for doc in self._collection.find({'user': user})]

    async def get_by_user_and_guild(self, user: int, guild: int) -> WarnInfo:
        doc = await self._collection.find_one({'user': user, 'guild': guild})
        return WarnInfo(**doc)

    async def apply(self, action: 'Act') -> WarnInfo:
        await self._collection.update_one({'user': action.user, 'guild': action.guild}, {'$inc': {'count': 1}}, upsert=True)
        warn = [w for w in await self.get(action.user) if w.guild == action.guild][0]
        if warn.count >= 3:
            await self._collection.delete_one({'user': action.user, 'guild': action.guild})
        return warn

    async def apply_remove(self, action: 'Act') -> WarnInfo:
        warn = await self.get_by_user_and_guild(action.user, action.guild)
        if warn.count <= 0:
            raise ValueError('У пользователя нет предупреждений')
        if warn.count == 1:
            await self._collection.delete_one({'user': action.user, 'guild': action.guild})
        else:
            await self._collection.update_one({'user': action.user, 'guild': action.guild}, {'$inc': {'count': -1}})
        return warn

    async def give(
            self, *,
            user: int, guild: int, moderator: int,
            reason: str, auto_review: bool = False
    ) -> 'Act':
        action = await self._actions.record(
            user, guild, moderator, 'warn_give',
            reason=reason, auto_review=auto_review
        )
        return action

    async def remove(self, user: int, guild: int, moderator: int, auto_review: bool = False) -> 'Act':
        warn = await self.get_by_user_and_guild(user, guild)
        if warn.count == 0:
            raise ValueError('У пользователя нет предупреждений')

        action = await self._actions.record(user, guild, moderator, 'warn_remove', counting=False, auto_review=auto_review)
        return action
