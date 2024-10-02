import datetime
from dataclasses import dataclass, asdict
from typing import Literal

import discord
from motor.motor_asyncio import AsyncIOMotorCollection as MotorCollection

import buttons
import templates

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


def _action_category(action_type: action) -> str:
    return 'roles' if 'role' in action_type else 'punishments'


_log_channels = {
    'roles': "логи-ролей",
    'punishments': "выдача-наказаний"
}


@dataclass
class Act:
    id: int
    at: datetime.datetime
    user: int
    guild: int
    moderator: int
    type: action
    counting: bool
    _id: str = None
    reviewer: int = None
    duration: float = None
    reason: str = None
    prove_link: str = None

    @property
    def as_dict(self):
        data = asdict(self)
        data.pop('_id')
        return data

    def _log_channel(self, guild: discord.Guild) -> discord.TextChannel:
        search = _log_channels[_action_category(self.type)]
        for channel in guild.text_channels:
            if channel.name == search:
                return channel
        raise ValueError(f'Не найден канал логов {search}')

    def to_embed(self, under_verify: bool, **objects) -> discord.Embed:
        embed = discord.Embed(
            title=templates.action(self.type),
            color=discord.Color.gold() if under_verify else discord.Color.random(),
            timestamp=self.at
        )
        
        embed.add_field(name='Пользователь', value=templates.user(objects['user']))
        embed.add_field(name='Модератор', value=templates.user(objects['moderator']))
        embed.set_footer(text=f'Акт №{self.id}')
        
        if self.reviewer:
            embed.add_field(name='Проверяющий', value=templates.user(objects['reviewer']))

        if self.duration:
            embed.add_field(name='Длительность', value=templates.time(self.duration))
        if self.prove_link:
            embed.add_field(name='Доказательство', value=templates.link(self.prove_link), inline=False)
        if self.reason:
            embed.add_field(name='Причина', value=self.reason, inline=False)
        return embed

    async def log(self, guild: discord.Guild, **objects) -> discord.Message:
        channel = self._log_channel(guild)
        embed = self.to_embed(under_verify=True, **objects)
        
        return await channel.send(templates.embed_mentions(embed), embed=embed, view=buttons.punishment_review(self.id))


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
    ) -> Act:
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
        await self._collection.insert_one(act.as_dict)
        return act
    
    async def deactivate(self, act_id: int, reviewer: int) -> None:
        await self._collection.update_one({'id': act_id}, {'$set': {'reviewer': reviewer, 'counting': False}})
    
    async def approve(self, act_id: int, reviewer: int) -> None:
        await self._collection.update_one({'id': act_id}, {'$set': {'reviewer': reviewer}})
        