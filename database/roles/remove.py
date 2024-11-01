import datetime
import enum
from dataclasses import dataclass, asdict

import discord

import buttons
import templates
from database.actions.action import Act
from info.roles import RoleInfo, role_info


@dataclass
class RolesRemove:
    id: int
    user: int
    guild: int
    roles: list[str]
    at: datetime.datetime
    moderator: int
    _id: str = None

    @property
    def role_info(self) -> list[RoleInfo]:
        return [role_info.get(role) for role in self.roles]

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop('_id')
        return data

    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title='🎭 Снятие ролей',
            color=discord.Color.light_embed(),
            timestamp=self.at.replace(tzinfo=datetime.timezone.utc)
        )

        embed.add_field(name='Пользователь', value=templates.user(self.user))
        embed.add_field(name='Модератор', value=templates.user(self.moderator))
        embed.add_field(name='Роли', value='\n'.join([role for role in self.roles]), inline=False)
        embed.set_footer(text=f'Снятие ролей №{self.id}')
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')

        return embed

    async def notify_user(self, user: discord.User, moderator: discord.Member = None):
        act = Act(id=self.id, at=datetime.datetime.now(datetime.UTC), user=self.user, guild=self.guild, moderator=self.moderator, type='role_remove', counting=False)
        await act.notify_user(self.to_embed(), user=user, moderator=moderator)
