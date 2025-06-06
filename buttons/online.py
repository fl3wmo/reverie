import re

import discord
from discord import Interaction
from discord._types import ClientT

from buttons.utils import int_to_base64, base64_to_int
from database import db
from core.templates import on_tree_error


class OnlineReload(discord.ui.DynamicItem[discord.ui.Button], template='online:reload:(?P<user_id>.+?):(?P<author_id>.+?):(?P<guild_id>.+?):(?P<is_open>[01]):(?P<date>.+)'):
    def __init__(self, user_id: int, author_id: int, guild_id: int, is_open: bool, date: str) -> None:
        super().__init__(
            discord.ui.Button(
                label='Обновить информацию',
                style=discord.ButtonStyle.secondary,
                custom_id=f'online:reload:{int_to_base64(user_id)}:{int_to_base64(author_id)}:{int_to_base64(guild_id)}:{int(is_open)}:{date}'
            )
        )
        self.user_id = user_id
        self.author_id = author_id
        self.guild_id = guild_id
        self.is_open = is_open
        self.date = date

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        user_id = base64_to_int(match.group('user_id'))
        author_id = base64_to_int(match.group('author_id'))
        guild_id = base64_to_int(match.group('guild_id'))
        is_open = bool(int(match.group('is_open')))
        date = match.group('date')
        return cls(user_id, author_id, guild_id, is_open, date)

    async def callback(self, interaction: Interaction[ClientT]):
        if interaction.user.id != self.author_id:
            return await on_tree_error(interaction, 'Это не ваше.')
        
        info = await db.online.get_info(self.is_open, self.user_id, self.guild_id, self.date)
        await interaction.response.edit_message(embed=info.to_embed(self.user_id, self.is_open, self.date), view=online_reload(self.user_id, self.author_id, self.guild_id, self.is_open, self.date))

def online_reload(user_id: int, author_id: int, guild_id: int, is_open: bool, date: str) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(OnlineReload(user_id, author_id, guild_id, is_open, date))
    return view
