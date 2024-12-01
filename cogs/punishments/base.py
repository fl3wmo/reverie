import re

import discord
from discord import app_commands
from discord.ext import commands

import security
import templates
from bot import EsBot
from database import db
from features import Pagination


class PunishmentsBase(commands.Cog, name='punishments'):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.punishments

    @app_commands.command(name='act', description='Выводит информацию о действии')
    @app_commands.describe(action='Порядковый номер действия для вывода информации')
    @app_commands.rename(action='номер-действия')
    @app_commands.default_permissions(manage_nicknames=True)
    async def act(self, interaction: discord.Interaction, action: int):
        action = await db.actions.get(action)
        if action is None:
            raise ValueError('Действие не найдено')
        embed = action.to_embed(under_verify=False)
        await interaction.response.send_message(templates.embed_mentions(embed), embed=embed, ephemeral=True)

    @app_commands.command(name='alist', description='Выводит список нарушений пользователя')
    @app_commands.describe(user='ID пользователя для вывода списка нарушений', global_alist='Выводить нарушения на всех серверах (DS+)')
    @app_commands.rename(user='id-пользователя', global_alist='глобальный')
    @app_commands.default_permissions(manage_nicknames=True)
    async def alist(self, interaction: discord.Interaction, user: str, global_alist: bool):
        owner = interaction.user
        if global_alist and security.user_level(owner) <= security.PermissionLevel.DS:
            raise ValueError('Недостаточно прав для просмотра глобального списка')

        _, user = await self.bot.getch_any(interaction.guild, user)

        actions = list(enumerate(await db.actions.by_user(user.id, guild=interaction.guild.id if not global_alist else None, counting=True), 1))
        if not actions:
            raise ValueError('Наказаний не найдено')

        pagination = Pagination(
            bot=self.bot,
            interaction=interaction,
            owner=owner,
            data=actions,
            page_size=5,
            embed_title=f'📕 Наказания пользователя {user}'
        )

        await pagination.send_initial_message()

    async def revert_action(self, reviewer: discord.Member, action_id: int):
        action = await db.actions.get(action_id)
        if action is None:
            raise ValueError('Действие не найдено')
        await db.actions.deactivate(action_id, reviewer.id)
        
        if (result := re.search(r'mute_(?P<type>text|voice|full)_give', action.type)) is not None:
            mutes = self.bot.get_cog('mute')
            if len([a for a in db.punishments.mutes.current if a.action == action.id]) == 0:
                return
            
            guild = self.bot.get_guild(action.guild)
            if guild is None:
                raise ValueError('Сервер не найден')
            
            member = await self.bot.getch_member(guild, action.user, reviewer)
            if member:
                await mutes.manage_mute_role(member, action.guild, result.group('type'), 'remove')
            await self.db.mutes.remove(action.user, action.guild, reviewer.id, result.group('type'))


async def setup(bot: EsBot):
    await bot.add_cog(PunishmentsBase(bot))
