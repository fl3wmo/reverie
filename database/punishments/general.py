import typing

from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

if typing.TYPE_CHECKING:
    from database.actions.general import Actions
from database.punishments.mutes import Mutes


class Punishments:
    def __init__(self, client: MotorClient, actions: 'Actions'):
        self._client = client
        self._db = self._client['Punishments']
        self.mutes = Mutes(self._db['mutes'], actions)