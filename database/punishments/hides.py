import typing

from dataclasses import dataclass, asdict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

if typing.TYPE_CHECKING:
    from database.actions.general import Actions
    from database.actions.action import Act


@dataclass
class Hide:
    user: int
    guild: int
    moderator: int
    _id: ObjectId = None

    @property
    def as_dict(self):
        data = asdict(self)
        data.pop('_id')
        return data

    @property
    def id(self):
        return self._id



class Hides:
    def __init__(self, collection: MotorCollection, actions: 'Actions'):
        self._collection = collection
        self._actions = actions
        self.current: list[Hide] = []

    async def load(self):
        self.current = [Hide(**doc) async for doc in self._collection.find()]

    async def get(self, user: int) -> list[Hide]:
        return [Hide(**doc) async for doc in self._collection.find({'user': user})]

    async def give(
            self, *,
            user: int, guild: int, moderator: int
    ) -> 'Act':
        if await self._collection.count_documents({'user': user, 'guild': guild}):
            raise ValueError('У пользователя уже есть скрытие на этом сервере')

        action = await self._actions.record(
            user=user, guild=guild, action_type='hide_give', moderator=moderator,
            auto_review=True, counting=False
        )
        await self._collection.insert_one({'user': user, 'guild': guild, 'moderator': moderator})

        return action

    async def remove(self, user: int, moderator: int, guild: int = None) -> 'Act':
        query = {'user': user}
        if guild:
            query['guild'] = guild
        hide = await self._collection.find_one(query)
        
        if not hide:
            raise ValueError('У пользователя нет скрытия на этом сервере')

        act = await self._actions.record(
            user=user, guild=guild, moderator=moderator,
            action_type='hide_remove', counting=False, auto_review=True
        )

        await self._collection.delete_one({'_id': hide['_id']})
        self.current = [m for m in self.current if m.id != hide['_id']]
        return act
