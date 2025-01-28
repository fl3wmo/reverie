
import discord
from discord import app_commands
from discord.ext import commands

import security
import templates
from bot import EsBot
from database import db
from database.punishments.warns import Warns


@app_commands.default_permissions(manage_nicknames=True)
class WarnsCog(commands.Cog, name='warn'):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db: Warns = db.punishments.warns

    async def on_approve(self, interaction, action_id: int, user=None, auto_kick: bool = True) -> None:
        if not user:
            member, user = await self.bot.getch_any(interaction.guild, user)
            
        action = await db.actions.get(action_id)
        warn = await self.db.apply(action)

        guild = self.bot.get_guild(warn.guild)
        if warn.active_count >= 3:
            bans = self.bot.get_cog('ban')
            await bans.warns_end(interaction, user, guild, action)
        elif auto_kick:
            try:
                await guild.kick(user, reason=action.reason)
            except discord.HTTPException:
                pass

    async def on_remove_approve(self, action_id: int) -> None:
        action = await db.actions.get(action_id)
        await self.db.apply_remove(action)

    @app_commands.command(name='warn', description='Предупредить пользователя')
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.rename(user='пользователь', reason='причина', auto_kick='авто-кик')
    @app_commands.describe(
        user='Пользователь, которого нужно заблокировать',
        reason='Причина блокировки',
        auto_kick='Кикнуть пользователя'
    )
    @app_commands.autocomplete(reason=db.punishments.warns_autocomplete)
    @security.restricted(security.PermissionLevel.MD)
    async def warn_give(self, interaction: discord.Interaction, user: str,
                        reason: app_commands.Range[str, 1, 512], auto_kick: bool = True):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        auto_review = security.user_level(interaction.user) >= security.PermissionLevel.SMD
        need_proof = security.user_level(interaction.user) < security.PermissionLevel.GMD
        act = await self.db.give(
            user=user.id, guild=interaction.guild.id, moderator=interaction.user.id,
            reason=reason, auto_review=auto_review
        )

        if auto_review:
            await self.on_approve(interaction, act.id, user=user, auto_kick=auto_kick)

        await templates.link_action(interaction, act, force_proof=need_proof, user=user, moderator=interaction.user)

    @app_commands.command(name='unwarn', description='Снять предупреждение с пользователя')
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно снять предупреждение')
    @security.restricted(security.PermissionLevel.MD)
    async def warn_remove(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        auto_review = security.user_level(interaction.user) >= security.PermissionLevel.GMD
        act = await self.db.remove(user=user.id, moderator=interaction.user.id, guild=interaction.guild.id,
                                   auto_review=auto_review)

        if auto_review:
            await self.on_remove_approve(act.id)
        
        await templates.link_action(interaction, act, user=user, moderator=interaction.user)


async def setup(bot: EsBot):
    await bot.add_cog(WarnsCog(bot))
