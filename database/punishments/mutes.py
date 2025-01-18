import asyncio
import datetime
import typing

from typing import Literal, Awaitable, Callable, Optional
from dataclasses import dataclass, asdict

import discord
from discord import Object, app_commands
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

if typing.TYPE_CHECKING:
    from database.actions.general import Actions
    from database.actions.action import Act


@dataclass
class Mute:
    user: int
    type: Literal['voice', 'text', 'full']
    guild: int
    action: int
    start: datetime.datetime
    duration: float
    _id: ObjectId = None

    @property
    def as_dict(self):
        data = asdict(self)
        data.pop('_id')
        return data
    
    @property
    def id(self):
        return self._id
    
    @property
    def start_utc(self):
        return self.start if self.start.tzinfo else self.start.replace(tzinfo=datetime.timezone.utc)

    async def wait(self, callback):
        start_aware = self.start.replace(tzinfo=datetime.timezone.utc)
        try:
            end = start_aware + datetime.timedelta(seconds=self.duration)
        except OverflowError:
            end = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)

        wait_duration = (end - now).total_seconds()
        if wait_duration > 0:
            await asyncio.sleep((end - now).total_seconds())

        await callback(self)


class Mutes:
    def __init__(self, collection: MotorCollection, actions: 'Actions'):
        self._collection = collection
        self._actions = actions
        self._expiration_callback: Optional[Callable[[Mute], Awaitable[None]]] = None
        self.current: list[Mute] = []

    async def load(self):
        self.current = [Mute(**doc) async for doc in self._collection.find()]
        for mute in self.current:
            _ = asyncio.create_task(mute.wait(self._on_expiration))

    async def _on_expiration(self, mute: Mute):
        while not self._expiration_callback:
            await asyncio.sleep(0.1)

        if mute not in self.current:
            return

        await self._collection.delete_one({'_id': mute.id})
        self.current.remove(mute)

        await self._expiration_callback(mute)

    def set_callback(self, callback: Callable[[Mute], Awaitable[None]]):
        self._expiration_callback = callback

    async def get(self, user: int) -> list[Mute]:
        return [Mute(**doc) async for doc in self._collection.find({'user': user})]

    async def give(
        self, *,
        user: int, guild: int, moderator: int, mute_type: Literal['voice', 'text', 'full'],
        duration: float, reason: str, auto_review: bool = False
    ) -> tuple['Act', Mute]:
        if await self._collection.count_documents({'user': user, 'type': mute_type, 'guild': guild}):
            raise ValueError('У пользователя уже есть мут на этом сервере')

        action = await self._actions.record(
            user, guild, moderator, f'mute_{mute_type}_give',
            duration=duration, reason=reason, auto_review=True
        )

        mute = Mute(
            user=user, type=mute_type, guild=guild, action=action.id,
            start=datetime.datetime.now(datetime.UTC), duration=duration
        )

        insert_info = await self._collection.insert_one(mute.as_dict)
        mute._id = insert_info.inserted_id

        self.current.append(mute)
        _ = asyncio.create_task(mute.wait(self._on_expiration))
        
        return action, mute

    async def remove(self, user: int, guild: int, moderator: int, mute_type: Literal['voice', 'text', 'full'], auto_review: bool = False) -> 'Act':
        mute = await self._collection.find_one({'user': user, 'type': mute_type, 'guild': guild})
        if not mute:
            raise ValueError('У пользователя нет мута на этом сервере')

        action = await self._actions.record(
            user, guild, moderator, f'mute_{mute_type}_remove',
            counting=False, auto_review=auto_review or mute.get('moderator') == moderator
        )

        await self._collection.delete_one({'_id': mute['_id']})
        self.current = [m for m in self.current if m.id != mute['_id']]
        return action
    
    async def users_autocomplete(self, mute_type: str, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        mutes = []
        for mute in sorted(self.current, key=lambda m: m.start_utc, reverse=True):
            if mute.type != mute_type or mute.guild != interaction.guild.id or (current and current.lower() not in str(mute.user).lower()):
                continue

            user = interaction.guild.get_member(mute.user) or Object(mute.user)
            
            start_aware = mute.start.replace(tzinfo=datetime.timezone.utc) if mute.start.tzinfo is None else mute.start
            elapsed = datetime.datetime.now(datetime.UTC) - start_aware
            elapsed_str = f'{int(elapsed.total_seconds() // 3600)}ч {int((elapsed.total_seconds() % 3600) // 60)}м назад'
            name = (
                f"{user.display_name} ({elapsed_str})" 
                if isinstance(user, discord.Member) 
                else f"{user.id} ({elapsed_str})"
            )
            mutes.append(app_commands.Choice(name=name, value=str(user.id)))
        return mutes[:20]
    
    async def users_autocomplete_text(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self.users_autocomplete('text', interaction, current)
    
    async def users_autocomplete_voice(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self.users_autocomplete('voice', interaction, current)
    
    async def users_autocomplete_full(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self.users_autocomplete('full', interaction, current)
    