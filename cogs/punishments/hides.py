import datetime

import discord
from discord import app_commands
from discord.ext import commands

import security
import templates
from bot import EsBot
from database import db


class HideCog(commands.Cog, name='hide'):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.punishments.hides

    @app_commands.command(name='hide', description='Скрыть пользователя')
    @app_commands.rename(user='пользователь')
    @app_commands.describe(
        user='Пользователь, которого нужно скрыть',
    )
    @app_commands.default_permissions(manage_nicknames=True)
    @security.restricted(security.PermissionLevel.MD)
    async def hide_give(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)
        if not member:
            raise ValueError('Пользователь не найден')
        
        await member.timeout(datetime.timedelta(days=27), reason=f'Скрытие от модератора {interaction.user.id}')
        act = await self.db.give(user=user.id, guild=interaction.guild.id, moderator=interaction.user.id)

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @app_commands.command(name='unhide', description='Убрать скрытие с пользователя')
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно убрать скрытие')
    @app_commands.default_permissions(manage_nicknames=True)
    @security.restricted(security.PermissionLevel.MD)
    async def hide_remove(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)
        if not member:
            raise ValueError('Пользователь не найден')

        await member.timeout(None)
        act = await self.db.remove(user=user.id, guild=interaction.guild.id, moderator=interaction.user.id)

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        hides = await self.db.get(member.id)

        if len([hide for hide in hides if hide.guild == member.guild.id or hide.guild is None]) > 0:
            if not member.is_timed_out():
                return await member.timeout(datetime.timedelta(days=27), reason='Скрытие')
        elif member.is_timed_out():
            await member.timeout(None)

async def setup(bot: EsBot):
    await bot.add_cog(HideCog(bot))
