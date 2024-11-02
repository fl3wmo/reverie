import typing
import datetime
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from database.roles.remove import RolesRemove
from database.roles.request import RoleRequest

if typing.TYPE_CHECKING:
    from database.actions.general import Actions

class Roles:
    def __init__(self, client: MotorClient, actions: 'Actions'):
        self._client = client
        self._db = self._client['Roles']
        self._col = self._db['Requests']
        self._remove_col = self._db['RemovedRoles']
        self.reasons_dict = {
            "/c 60": ('⏱️', "На скриншоте не видно точного времени."),
            "Номер сервера": ('🔢', "На скриншоте не видно номера сервера или он не совпадает."),
            "Нет доказательств": ('⁉️', "Скриншот не с игры либо не видно статистику / удостоверение."),
            "24 часа": ('⌛', "Скриншоту больше 24 часов."),
            "Не в организации": ('🧑‍💼', "На скриншоте не видно док-в пребывания в указанной организации."),
            "Никнейм": ('📛', "На скриншоте не совпадает никнейм с указанным."),
        }

    async def get_request(self, user: int, guild: int) -> RoleRequest | None:
        result = await self._col.find_one({'user': user, 'guild': guild, 'checked_at': None})
        return RoleRequest(**result) if result else None

    async def get_request_by_id(self, request_id: int) -> RoleRequest | None:
        result = await self._col.find_one({'id': request_id})
        return RoleRequest(**result) if result else None

    async def is_request_last(self, request_id: int, user: int, guild: int) -> bool:
        result = await self._col.find_one({'user': user, 'guild': guild, 'id': {'$gt': request_id}})
        return result is None

    async def add_request(self, user: int, guild: int, nickname: str, role: str, rang: int, status_message: int) -> RoleRequest:
        req_id = (await self._col.count_documents({})) + 1
        req = RoleRequest(
            id=req_id, user=user, guild=guild, nickname=nickname, role=role, rang=rang, counting=True,
            approved=False, sent_at=datetime.datetime.now(datetime.timezone.utc), status_message=status_message
        )
        await self._col.insert_one(req.to_dict())
        return req

    async def take_request(self, request_id: int, moderator: int) -> None:
        await self._col.update_one({'id': request_id}, {'$set': {'moderator': moderator, 'taken_at': datetime.datetime.now(datetime.timezone.utc)}})

    async def check_request(self, moderator: int, request_id: int, approve: bool, reason: str = None) -> None:
        if moderator != (await self.get_request_by_id(request_id)).moderator:
            raise ValueError('Заявлением занимается другой модератор')
        await self._col.update_one(
            {'id': request_id},
            {'$set': {
                'approved': approve, 'checked_at': datetime.datetime.now(datetime.timezone.utc),
                'moderator': moderator, 'reason': reason
            }}
        )

    async def review_request(self, reviewer: int, request_id: int, approve: bool, reason: str = None, partial: bool = False) -> None:
        update = {'$set': {'reviewer': reviewer}}
        if not approve:
            request = await self.get_request_by_id(request_id)
            update['$set']['approved'] = not request.approved
            if not request.approved:
                update['$set']['review_reason'] = reason
            else:
                update['$set']['reason'] = reason
        if partial:
            update['$set']['counting'] = False
            update['$set']['review_reason'] = reason
        await self._col.update_one({'id': request_id}, update)

    async def remove_roles(self, user: int, guild: int, roles: list[str], moderator: int) -> RolesRemove:
        roles = sorted(roles)
        remove_id = (await self._remove_col.count_documents({})) + 1
        remove = RolesRemove(
            id=remove_id, user=user, guild=guild, roles=roles, at=datetime.datetime.now(datetime.timezone.utc), moderator=moderator
        )
        await self._remove_col.insert_one(remove.to_dict())
        return remove

    async def moderator_work(self, guild: int, moderator: int, date_from: datetime.datetime, date_to: datetime.datetime = None) -> tuple[list[RoleRequest], list[RolesRemove]]:
        date_from = date_from.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(hours=3)
        if date_to:
            date_to = date_to.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(hours=3)
        cursor_requests = self._col.find({'guild': guild, 'moderator': moderator, 'counting': True, 'sent_at': {'$gte': date_from, '$lte': date_to or (date_from + datetime.timedelta(days=1))}})
        cursor_removes = self._remove_col.find({'guild': guild, 'moderator': moderator, 'at': {'$gte': date_from, '$lte': date_to or (date_from + datetime.timedelta(days=1))}})
        return [RoleRequest(**doc) async for doc in cursor_requests], [RolesRemove(**doc) async for doc in cursor_removes]

    async def role_history(self, guild: int, user: int) -> list[RoleRequest]:
        return [RoleRequest(**doc) async for doc in self._col.find({'guild': guild, 'user': user})]
    