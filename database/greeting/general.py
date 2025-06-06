from typing import Literal

from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from database.greeting.settings import GreetingSettings

Location = Literal["dm", "channel"]


class Greeting:
    def __init__(self, client: MotorClient):
        self._client = client
        self._db = self._client['Reverie']
        self._col = self._db['greeting']

    async def get_settings(self, guild: int) -> GreetingSettings | None:
        result = await self._col.find_one({'guild': guild})
        return GreetingSettings(**result) if result else GreetingSettings(guild=guild)

    async def set_text(self, guild: int, new_text: str, where: Location) -> None:
        await self._col.update_one(
            {'guild': guild},
            {'$set': {f'{where}_text': new_text}},
            upsert=True
        )

    async def set_enabled(self, guild: int, where: Location, enabled: bool) -> None:
        await self._col.update_one(
            {'guild': guild},
            {'$set': {f'{where}_enabled': enabled}},
            upsert=True
        )

    async def set_channel(self, guild: int, channel: int) -> None:
        await self._col.update_one(
            {'guild': guild},
            {'$set': {'guild_channel': channel}},
            upsert=True
        )
