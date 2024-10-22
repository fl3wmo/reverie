import typing
import datetime
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient
from database.roles.request import RoleRequest

if typing.TYPE_CHECKING:
    from database.actions.general import Actions

class Roles:
    def __init__(self, client: MotorClient, actions: 'Actions'):
        self._client = client
        self._db = self._client['Roles']
        self._col = self._db['Requests']
        self.reasons_dict = {
            "/c 60": ('⏱️', "На скриншоте не видно точного времени."),
            "Номер сервера": ('🔢', "На скриншоте не видно номера сервера или он не совпадает."),
            "Невалид": ('⁉️', "Скриншот не с игры либо не видно статистику / удостоверение."),
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
        await self._col.update_one({'id': request_id}, {'$set': {'moderator': moderator}})

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

    async def review_request(self, reviewer: int, request_id: int, approve: bool, partial: bool = False) -> None:
        update = {'$set': {'reviewer': reviewer}}
        if not approve:
            request = await self.get_request_by_id(request_id)
            update['$set']['approved'] = not request.approved
        if partial:
            update['$set']['counting'] = False
        await self._col.update_one({'id': request_id}, update)
        