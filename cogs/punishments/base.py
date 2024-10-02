import re

import discord
from discord import app_commands
from discord.ext import commands

from bot import EsBot
from database import db


class PunishmentsBase(commands.Cog, name='punishments'):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.punishments

    @app_commands.command(name='act', description='Выводит информацию о действии')
    @app_commands.describe(action='Порядковый номер действия для вывода информации')
    @app_commands.rename(action='номер-действия')
    async def act(self, interaction: discord.Interaction, action: int):
        raise NotImplementedError
        
    async def revert_action(self, reviewer: discord.Member, action_id: int):
        action = await db.actions.get(action_id)
        if action is None:
            raise ValueError('Действие не найдено')
        await db.actions.deactivate(action_id, reviewer.id)
        
        if (result := re.search(r'mute_(?P<type>text|voice|full)_give', action.type)) is not None:
            mutes = self.bot.get_cog('mute')
            if len([a for a in db.punishments.mutes.current if a.action == action.id]) == 0:
                raise ValueError('Действие истекло')
            
            guild = self.bot.get_guild(action.guild)
            if guild is None:
                raise ValueError('Сервер не найден')
            
            member, user = await self.bot.getch_any(guild, action.user, reviewer)
            if member:
                await mutes.manage_mute_role(action.user, action.guild, result.group('type'), 'remove')
            await self.db.mutes.remove(action.user, action.guild, reviewer.id, result.group('type'))


async def setup(bot: EsBot):
    await bot.add_cog(PunishmentsBase(bot))
