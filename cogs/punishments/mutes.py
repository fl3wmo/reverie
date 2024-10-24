import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

import security
import templates
import validation
from bot import EsBot
from database import db


class MutesModal(discord.ui.Modal, title='Выдача текстового мута'):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mute_callback = callback

    duration = discord.ui.TextInput(label='Длительность', placeholder='1ч', min_length=1, max_length=50)
    reason = discord.ui.TextInput(label='Причина', placeholder='Причина не указана', min_length=1, max_length=50)
    message_amount = discord.ui.TextInput(label='Количество сообщений', default='10', placeholder='10', min_length=1, max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.message_amount.value.isdecimal() or int(self.message_amount.value) > 99:
            raise ValueError('Количество сообщений должно быть числом от 1 до 100')
        duration_in_seconds = validation.parse_duration(self.duration.value, 'м')
        await self.mute_callback(interaction, duration_in_seconds, self.reason.value, int(self.message_amount.value))


@app_commands.default_permissions(manage_nicknames=True)
class MutesCog(commands.GroupCog, name='mute'):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.punishments.mutes
        self.ctx_menu = app_commands.ContextMenu(
            name='текстовый мут', callback=self.mute_text_screen
        )
        self.bot.tree.add_command(self.ctx_menu)

    text = app_commands.Group(name='text', description='Муты в текстовых каналах', guild_only=True)
    voice = app_commands.Group(name='voice', description='Муты в голосовых каналах', guild_only=True)
    full = app_commands.Group(name='full', description='Полный мут', guild_only=True)

    async def mute_text_give(self, interaction: discord.Interaction, user: str | discord.Member | discord.User, duration: str, reason: str, *, screenshot: tuple[discord.Message, int] | None = None):
        if isinstance(user, str):
            member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)
        elif isinstance(user, discord.Member):
            member = user
        else:
            member = None

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'text', 'add')

        act, mute = await self.db.give(
            user=user.id, guild=interaction.guild.id, moderator=interaction.user.id,
            mute_type='text', duration=duration, reason=reason
        )

        full_screenshot = None
        if screenshot:
            full_screenshot = [mess async for mess in screenshot[0].channel.history(around=screenshot[0], limit=screenshot[1])]
        else:
            screenshot = (None, 0)
        await templates.link_action(interaction, act, full_screenshot, screenshot[0], db, user=user, moderator=interaction.user)

    @text.command(name='give', description='Замутить пользователя в текстовых каналах')
    @app_commands.rename(user='пользователь', duration='длительность', reason='причина')
    @app_commands.describe(
        user='Пользователь, которого нужно замутить',
        duration='Длительность в формате dF. Примеры: 1с, 1м, 1ч',
        reason='Причина мута'
    )
    @app_commands.autocomplete(reason=db.punishments.reasons_autocomplete)
    @validation.duration_formatter()
    @security.restricted(security.PermissionLevel.MD)
    async def mute_text(self, interaction: discord.Interaction, user: str, duration: str,
                        reason: app_commands.Range[str, 1, 512]):
        await self.mute_text_give(interaction, user, duration, reason)

    async def mute_text_screen(self, interaction: discord.Interaction, message: discord.Message):
        if security.user_level(interaction.user) < security.PermissionLevel.MD:
            raise ValueError('У вас нет прав')
        security.user_permissions_compare(interaction.user, message.author)
        async def mute_callback(modal_interaction, duration, reason, message_amount: int):
            await self.mute_text_give(modal_interaction, message.author, duration, reason, screenshot=(message, message_amount))
        await interaction.response.send_modal(MutesModal(mute_callback))

    @text.command(name='remove', description='Снять мут с пользователя в текстовых каналах')
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, с которого нужно снять мут')
    @security.restricted(security.PermissionLevel.MD)
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
    @app_commands.autocomplete(reason=db.punishments.reasons_autocomplete)
    @validation.duration_formatter()
    @security.restricted(security.PermissionLevel.MD)
    async def mute_voice(
            self, interaction: discord.Interaction, user: str,
            duration: str, reason: app_commands.Range[str, 1, 512]
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
    @security.restricted(security.PermissionLevel.MD)
    async def unmute_voice(self, interaction: discord.Interaction, user: str):
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)

        if member:
            await self.manage_mute_role(member, interaction.guild.id, 'voice', 'remove')

        act = await self.db.remove(
            user=user.id, moderator=interaction.user.id, guild=interaction.guild.id, mute_type='voice',
            auto_review=security.user_level(interaction.user) > security.PermissionLevel.GMD
        )

        await templates.link_action(interaction, act, user=user, moderator=interaction.user)

    @full.command(name='give', description='Полный мут пользователя (в текстовых и голосовых каналах)')
    @app_commands.rename(user='пользователь', duration='длительность', reason='причина')
    @app_commands.describe(
        user='Пользователь, которого нужно замутить',
        duration='Длительность в формате dF. Примеры: 1с, 1м, 1ч',
        reason='Причина мута'
    )
    @app_commands.autocomplete(reason=db.punishments.reasons_autocomplete)
    @validation.duration_formatter()
    @security.restricted(security.PermissionLevel.MD)
    async def mute_full(
            self, interaction: discord.Interaction, user: str,
            duration: str, reason: app_commands.Range[str, 1, 512]
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
    @security.restricted(security.PermissionLevel.MD)
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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        mutes = [m for m in self.db.current if m.user == member.id and m.guild == member.guild.id]
        for mute in mutes:
            await self.manage_mute_role(member, member.guild.id, mute.type, 'add')

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
        del permissions['connect']
    elif mute_type == 'voice':
        del permissions['send_messages']
    elif mute_type == 'full':
        permissions["view_channel"] = False
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
            try:
                channel_overwrite = dict(permissions)
                for action in [a for a in unable_actions(channel) if a in channel_overwrite]:
                    channel_overwrite.pop(action)
                if 'правила' in channel.name:
                    channel_overwrite['view_channel'] = True
                if channel_overwrite:
                    await channel.set_permissions(mute_role, overwrite=discord.PermissionOverwrite(**channel_overwrite))
            except Exception as e:
                logging.error(f'Error while setting permissions for {channel.name}: {e}', exc_info=True)
                continue


async def apply_mute_action(user: discord.Member, mute_role: discord.Role, action: Literal['add', 'remove']):
    try:
        if action == 'remove':
            if mute_role not in user.roles:
                raise ValueError('Пользователь не в муте.')
            await user.remove_roles(mute_role)
        elif action == 'add':
            if mute_role in user.roles:
                raise ValueError('Пользователь уже в муте.')
            await user.add_roles(mute_role)
            if mute_role.permissions.speak == False and user.voice is not None:
                await user.edit(voice_channel=None)
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
