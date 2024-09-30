import datetime
from dataclasses import dataclass
from typing import Literal

from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

type action = Literal[
    'role_approve', 'role_reject', 'role_remove',
    'ban_give', 'ban_remove',
    'warn_give', 'warn_remove',
    'global_ban_give', 'global_ban_remove',
    'mute_text_give', 'mute_text_remove',
    'mute_voice_give', 'mute_voice_remove',
    'mute_full_give', 'mute_full_remove',
    'temp_mute_give', 'temp_mute_remove',
]

@dataclass
class Act:
    id: int
    at: datetime.datetime
    user: int
    guild: int
    moderator: int
    type: action
    counting: bool
    reviewer: int = None
    duration: float = None
    reason: str = None
    prove_link: str = None


class Actions:
    def __init__(self, collection: MotorCollection):
        self._collection = collection

    async def get(self, act_id: int) -> Act:
        return Act(**await self._collection.find_one({'id': act_id}))

    async def by_user(self, user: int) -> list[Act]:
        return [Act(**doc) async for doc in self._collection.find({'user': user})]

    async def record(
            self, user: int, guild: int,
            moderator: int, action_type: action, *,
            counting: bool = True, duration: float = None,
            reason: str = None, prove_link: str = None
    ) -> int:
        act_id = (await self._collection.count_documents({})) + 1
        act = Act(
            id=act_id,
            at=datetime.datetime.now(datetime.UTC),
            user=user,
            guild=guild,
            moderator=moderator,
            type=action_type,
            counting=counting,
            duration=duration,
            reason=reason,
            prove_link=prove_link
        )
        await self._collection.insert_one(act.__dict__)
        return act_id
