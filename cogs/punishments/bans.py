import typing

import discord
from discord import app_commands, Object
from discord.ext import commands

import security
import templates
import validation
from bot import Reverie
from database import db

if typing.TYPE_CHECKING:
    from database.punishments.bans import Bans


class BansCog(commands.Cog, name='ban'):
    def __init__(self, bot: Reverie):
        self.bot = bot
        self.db: Bans = db.punishments.bans

    async def on_approve(self, action_id: int) -> None:
        action = await db.actions.get(action_id)
        ban = await self.db.apply(action)
        try:
            await db.punishments.hides.remove(
                user=ban.user,
                guild=ban.guild if ban.type == 'local' else None,
                moderator=action.moderator
            )
        except:
            pass

        user = await self.bot.getch_user(ban.user)
        moderator = await self.bot.getch_member(self.bot.get_guild(ban.guild), action.moderator)

        try:
            await action.notify_user(user=user, moderator=moderator)
        except:
            pass

        guilds = [self.bot.get_guild(ban.guild)] if ban.type == 'local' else self.bot.guilds
        for guild in guilds:
            try:
                await guild.ban(Object(id=ban.user), reason=action.reason)
            except discord.Forbidden:
                pass

    async def warns_end(self, interaction, user: discord.User, guild: discord.Guild, action):
        ban_act = await self.db.give(
            user=user.id, guild=guild.id, moderator=action.moderator,
            ban_type='local', duration=10 * 24 * 60 * 60, reason='3 предупреждения',
            counting=False, auto_review=True
        )
        await self.on_approve(ban_act.id)
        await templates.link_action(interaction, ban_act, moderator=interaction.user, user=user)

    @app_commands.command(name='gban', description='Заблокировать пользователя на всех серверах')
    @app_commands.default_permissions(administrator=True)
    @app_commands.rename(user='пользователь', duration='длительность', reason='причина')
    @app_commands.describe(
        user='Пользователь, которого нужно заблокировать',
        duration='Длительность в формате dF. Примеры: 1с, 1м, 1ч',
        reason='Причина блокировки'
    )
    @app_commands.autocomplete(reason=db.punishments.bans_autocomplete)
    @validation.duration_formatter(default_unit="д")
    @security.restricted(security.PermissionLevel.CUR)
    async def ban_global(self, interaction: discord.Interaction, user: str, duration: str,
                        reason: app_commands.Range[str, 1, 512]):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        auto_review = True
        act = await self.db.give(
            user=user.id, guild=interaction.guild.id, moderator=interaction.user.id,
            ban_type='global', duration=duration, reason=reason, auto_review=auto_review
        )

        await templates.link_action(interaction, act, user=user, moderator=interaction.user, notify_user=False, auto_review=auto_review)

        if auto_review:
            await self.on_approve(act.id)

    @app_commands.command(name='ungban', description='Снять блокировку с пользователя на всех серверах')
    @app_commands.default_permissions(administrator=True)
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно снять блокировку')
    @security.restricted(security.PermissionLevel.CUR)
    async def unban_global(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        for guild in self.bot.guilds:
            try:
                await guild.unban(user)
            except discord.Forbidden:
                pass
            
        act = await self.db.remove(user=user.id, moderator=interaction.user.id, guild=interaction.guild.id, ban_type='global')
        
        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @app_commands.command(name='ban', description='Заблокировать пользователя на этом сервере')
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.rename(user='пользователь', duration='длительность', reason='причина')
    @app_commands.describe(
        user='Пользователь, которого нужно заблокировать',
        duration='Длительность в формате dF. Примеры: 1с, 1м, 1ч',
        reason='Причина блокировки'
    )
    @app_commands.autocomplete(reason=db.punishments.bans_autocomplete)
    @validation.duration_formatter(default_unit="д")
    @security.restricted(security.PermissionLevel.MD)
    async def ban_local(self, interaction: discord.Interaction, user: str, duration: str,
                         reason: app_commands.Range[str, 1, 512]):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        auto_review = security.user_level(interaction.user) >= security.PermissionLevel.GMD
        act = await self.db.give(
            user=user.id, guild=interaction.guild.id, moderator=interaction.user.id,
            ban_type='local', duration=duration, reason=reason, auto_review=auto_review
        )

        await templates.link_action(interaction, act, user=user, moderator=interaction.user, notify_user=False, auto_review=auto_review)

        if auto_review:
            await self.on_approve(act.id)

    @app_commands.command(name='unban', description='Снять блокировку с пользователя на этом сервере')
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно снять блокировку')
    @security.restricted(security.PermissionLevel.GMD)
    async def unban_local(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        await interaction.guild.unban(user)

        act = await self.db.remove(user=user.id, moderator=interaction.user.id, guild=interaction.guild.id,
                                   ban_type='local')

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @commands.Cog.listener()
    async def on_connect(self):
        self.db.set_callback(self.on_ban_expiration)
        await self.db.load()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        is_ban = bool([b for b in self.db.current if b.type == 'global' and b.user == member.id])
        if is_ban:
            await member.ban(reason='Глобальный бан')

    async def on_ban_expiration(self, ban):
        guilds = [self.bot.get_guild(ban.guild)] if ban.type == 'local' else self.bot.guilds
        for guild in guilds:
            try:
                await guild.unban(Object(id=ban.user))
            except discord.Forbidden:
                pass

async def setup(bot: Reverie):
    await bot.add_cog(BansCog(bot))
