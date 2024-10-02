from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

import security
import templates
from bot import EsBot
from database import db
    

class MutesCog(commands.GroupCog, name='mute'):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.punishments.mutes

    text = app_commands.Group(name='text', description='Муты в текстовых каналах', guild_only=True)
    voice = app_commands.Group(name='voice', description='Муты в голосовых каналах', guild_only=True)
    full = app_commands.Group(name='full', description='Полный мут', guild_only=True)

    @text.command(name='give', description='Замутить пользователя в текстовых каналах')
    @app_commands.rename(user='пользователь', duration='длительность', reason='причина')
    @app_commands.describe(
        user='Пользователь, которого нужно замутить',
        duration='Длительность в формате dF. Примеры: 1с, 1м, 1ч',
        reason='Причина мута'
    )
    @templates.duration_formatter()
    @security.restricted(1)
    async def mute_text(self, interaction: discord.Interaction, user: str, duration: str,
                        reason: app_commands.Range[str, 1, 50]):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'text', 'add')

        act, mute = await self.db.give(
            user=user.id, guild=interaction.guild.id, moderator=interaction.user.id,
            mute_type='text', duration=duration, reason=reason
        )
        
        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @text.command(name='remove', description='Снять мут с пользователя в текстовых каналах')
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно снять мут')
    @security.restricted(1)
    async def unmute_text(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'text', 'remove')
        act = await self.db.remove(user=user.id, moderator=interaction.user.id, guild=interaction.guild.id, mute_type='text')
        
        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @voice.command(name='give', description='Замутить пользователя в голосовых каналах')
    @app_commands.rename(user='пользователь', duration='длительность', reason='причина')
    @app_commands.describe(
        user='Пользователь, которого нужно замутить',
        duration='Длительность в формате dF. Примеры: 1с, 1м, 1ч',
        reason='Причина мута'
    )
    @templates.duration_formatter()
    @security.restricted(1)
    async def mute_voice(
            self, interaction: discord.Interaction, user: str,
            duration: str, reason: app_commands.Range[str, 1, 50]
    ):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'voice', 'add')

        act, mute = await self.db.give(
            user=user.id, guild=interaction.guild.id, moderator=interaction.user.id,
            mute_type='voice', duration=duration, reason=reason
        )

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @voice.command(name='remove', description='Снять мут с пользователя в голосовых каналах')
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно снять мут')
    @security.restricted(1)
    async def unmute_voice(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'voice', 'remove')

        act = await self.db.remove(
            user=user.id, moderator=interaction.user.id, guild=interaction.guild.id, mute_type='voice'
        )

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @full.command(name='give', description='Полный мут пользователя (в текстовых и голосовых каналах)')
    @app_commands.rename(user='пользователь', duration='длительность', reason='причина')
    @app_commands.describe(
        user='Пользователь, которого нужно замутить',
        duration='Длительность в формате dF. Примеры: 1с, 1м, 1ч',
        reason='Причина мута'
    )
    @templates.duration_formatter()
    @security.restricted(1)
    async def mute_full(
            self, interaction: discord.Interaction, user: str,
            duration: str, reason: app_commands.Range[str, 1, 50]
    ):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'full', 'add')

        act, mute = await self.db.give(
            user=user.id, guild=interaction.guild.id, moderator=interaction.user.id,
            mute_type='full', duration=duration, reason=reason
        )

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @full.command(name='remove', description='Снять полный мут с пользователя')
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно снять полный мут')
    @security.restricted(1)
    async def unmute_full(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'full', 'remove')

        act = await self.db.remove(
            user=user.id, moderator=interaction.user.id, guild=interaction.guild.id, mute_type='full'
        )

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @commands.Cog.listener()
    async def on_connect(self):
        self.db.set_callback(self.on_mute_expiration)
        await self.db.load()

    async def manage_mute_role(self, user: discord.Member, guild_id: int, mute_type: str,
                               action: Literal['add', 'remove']):
        guild = self.bot.get_guild(guild_id)
        mute_role = await get_or_create_mute_role(guild, mute_type)
        await apply_mute_action(user, mute_role, action)

    async def on_mute_expiration(self, mute):
        guild = self.bot.get_guild(mute.guild)
        member = await self.bot.getch_member(guild, mute.user)
        if member is not None:
            await self.manage_mute_role(member, guild.id, mute.type, 'remove')


def mute_restrictions(mute_type: str) -> dict:
    permissions = {"connect": False, "send_messages": False}

    if mute_type == 'text':
        permissions.pop('connect')
    elif mute_type == 'voice':
        permissions.pop('send_messages')
    return permissions


def unable_actions(channel: discord.abc.GuildChannel) -> list[str]:
    actions = []
    if 'send' not in dir(channel):
        actions.append('send_messages')
    if 'connect' not in dir(channel):
        actions.append('connect')
    return actions


async def create_roles(guild: discord.Guild):
    for mute_type in ('voice', 'text', 'full'):
        role_name = f'Mute » {mute_type.capitalize()}'
        if discord.utils.get(guild.roles, name=role_name) is not None:
            continue

        permissions = mute_restrictions(mute_type)
        mute_role = await guild.create_role(name=f'Mute » {mute_type.capitalize()}',
                                            permissions=discord.Permissions(**permissions))

        for channel in guild.channels:
            channel_overwrite = dict(permissions)
            for action in unable_actions(channel):
                channel_overwrite.pop(action)
            if channel_overwrite:
                await channel.set_permissions(mute_role, overwrite=discord.PermissionOverwrite(**channel_overwrite))


async def apply_mute_action(user: discord.Member, mute_role: discord.Role, action: Literal['add', 'remove']):
    try:
        if action == 'remove':
            await user.remove_roles(mute_role)
        elif action == 'add':
            await user.add_roles(mute_role)
    except discord.Forbidden:
        raise ValueError('У меня нет прав.')


async def get_or_create_mute_role(guild: discord.Guild, mute_type: str) -> discord.Role:
    role_name = f'Mute » {mute_type.capitalize()}'
    mute_role = discord.utils.get(guild.roles, name=role_name)
    if mute_role is None:
        await create_roles(guild)
        mute_role = discord.utils.get(guild.roles, name=role_name)
        if mute_role is None:
            raise ValueError('Роль не найдена.')
    return mute_role


async def setup(bot: EsBot):
    await bot.add_cog(MutesCog(bot))
