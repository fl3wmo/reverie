import logging
import os

import discord
from discord.ext import commands

import buttons
import security
import validation
from database import db
from templates import on_tree_error


class EsBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_ids = {}

    async def setup_hook(self) -> None:
        self.tree.error(on_tree_error)
        buttons.load_buttons(self)
        await db.on_load()
        await self.load_extensions()

    async def load_extensions(self):
        for filename in os.listdir('./cogs'):
            if '__' not in filename:
                filename = filename.replace('.py', '')
                await self.load_extension(f'cogs.{filename}')
                logging.info(f'Loaded {filename}')
    
    @staticmethod
    async def getch_member(
            guild: discord.Guild, user_id: int, guard_compare: discord.Member | None = None
    ) -> discord.Member | None:
        if isinstance(user_id, str):
            user_id = validation.user_id(user_id)
        try:
            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
            if guard_compare is not None:
                security.user_permissions_compare(guard_compare, member)
            return member
        except discord.NotFound:
            return None
        except discord.HTTPException:
            return None

    async def getch_user(self, user_id: int) -> discord.User | None:
        try:
            return self.get_user(user_id) or await self.fetch_user(user_id)
        except discord.NotFound:
            return None
        except discord.HTTPException:
            return None
    
    async def getch_any(
            self, guild: discord.Guild, user_id: int | str,
            guard_compare: discord.Member | None = None
    ) -> tuple[discord.Member | None, discord.Member | discord.User]:
        if isinstance(user_id, str):
            user_id = validation.user_id(user_id)

        if member := await self.getch_member(guild, user_id):
            if guard_compare is not None:
                security.user_permissions_compare(guard_compare, member)
            return member, member
        elif user := await self.getch_user(user_id):
            return None, user
        else:
            raise ValueError('Пользователь не найден.')


