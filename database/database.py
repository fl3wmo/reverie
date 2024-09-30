from motor.motor_asyncio import AsyncIOMotorClient

from database.actions.general import Actions
from database.punishments.general import Punishments


class Database:
    def __init__(self):
        self._client = AsyncIOMotorClient('mongodb://localhost:27017')
        self._db = self._client['EsBot']
        self.actions = Actions(self._db['actions'])
        self.punishments = Punishments(self._client, self.actions)
