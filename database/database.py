import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from database.actions.general import Actions
from database.notifications import Notifications
from database.online.general import OnlineDatabase
from database.punishments.general import Punishments
from database.roles.general import Roles


class Database:
    def __init__(self):
        load_dotenv()
        
        self._client = AsyncIOMotorClient(os.getenv('MONGO_URI'))
        self._db = self._client['Reverie']
        self.actions = Actions(self._db['actions'])
        self.punishments = Punishments(self._client, self.actions)
        self.roles = Roles(self._client, self.actions)
        self.online = OnlineDatabase('online.sqlite')
        self.notifications = Notifications(self._db['notifications'])

    async def on_load(self):
        await self.online.init_db()
    