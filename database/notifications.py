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
class Notification:
    user: int
    guild: int
    moderator: int
    type: str
    at: datetime.datetime
    duration: float
    message_id: int
    expired: bool = False
    notified: bool = False
    id: int = None
    _id: ObjectId = None

    @property
    def as_dict(self):
        data = asdict(self)
        data.pop('_id')
        return data
    
    async def wait(self, callback: Callable[['Notification'], Awaitable[None]]):
        start_aware = self.at.replace(tzinfo=datetime.timezone.utc)
        end = start_aware + datetime.timedelta(seconds=self.duration)
        now = datetime.datetime.now(datetime.timezone.utc)

        wait_duration = (end - now).total_seconds()
        if wait_duration > 0:
            await asyncio.sleep((end - now).total_seconds())

        await callback(self)

class Notifications:
    def __init__(self, collection: MotorCollection):
        self._collection = collection
        self._expiration_callback: Optional[Callable[[Notification], Awaitable[None]]] = None
        self.current: list[Notification] = []

    async def load(self):
        self.current = [Notification(**doc) async for doc in self._collection.find({'expired': False})]
        for notification in self.current:
            _ = asyncio.create_task(notification.wait(self._on_expiration))

    async def _on_expiration(self, notification: Notification):
        while not self._expiration_callback:
            await asyncio.sleep(0.1)

        if notification not in self.current:
            return

        await self._collection.update_one({"id": notification.id}, {'$set': {'expired': True}})
        self.current.remove(notification)

        await self._expiration_callback(notification)

    def set_callback(self, callback: Callable[[Notification], Awaitable[None]]):
        self._expiration_callback = callback

    async def get_by_id(self, id: int) -> Notification:
        return Notification(**await self._collection.find_one({'id': id, 'notified': False}))
    
    async def notify(self, notification: Notification) -> None:
        await self._collection.update_one({"id": notification.id}, {'$set': {'notified': True}})

    async def give(
            self, *,
            user: int, guild: int, moderator: int, notification_type: str, duration: float, message_id: int
    ) -> 'Act':
        notification_id = (await self._collection.count_documents({})) + 1

        notification = Notification(
            user=user, guild=guild, moderator=moderator, type=notification_type,
            at=datetime.datetime.now(datetime.timezone.utc), duration=duration,
            id=notification_id, message_id=message_id
        )

        await self._collection.insert_one(notification.as_dict)
        self.current.append(notification)
        _ = asyncio.create_task(notification.wait(self._on_expiration))

        return notification
