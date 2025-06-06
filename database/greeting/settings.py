import datetime
import enum
from dataclasses import dataclass, asdict

import discord

import buttons
from buttons.indicators import sent_from
from core import templates
from core.bot import Reverie
from database.actions.action import Act
from info.roles import RoleInfo, role_info

def format_message(text: str, for_member: discord.Member) -> str:
    placeholders = {
        '<user>': for_member.mention,
        '<user_id>': str(for_member.id),
        '<user_name>': for_member.display_name,
        '<guild_name>': for_member.guild.name,
    }
    for placeholder, value in placeholders.items():
        text = text.replace(placeholder, value)
    return text

@dataclass
class GreetingSettings:
    guild: int
    guild_enabled: bool = False
    dm_enabled: bool = False
    guild_text: str = ''
    dm_text: str = ''
    guild_channel: int = None
    _id: str = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop('_id')
        return data

    @property
    def enabled(self) -> bool:
        return self.guild_enabled or self.dm_enabled

    async def greet(self, new_member: discord.Member) -> None:
        if self.guild_enabled and self.guild_text:
            channel = new_member.guild.get_channel(self.guild_channel) or new_member.guild.system_channel
            if channel:
                await channel.send(format_message(self.guild_text, new_member))

        if self.dm_enabled and self.dm_text:
            try:
                await new_member.send(format_message(self.dm_text, new_member), view=sent_from(new_member.guild))
            except discord.Forbidden:
                pass