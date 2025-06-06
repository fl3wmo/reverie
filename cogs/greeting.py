import discord
from discord import app_commands
from discord.ext import commands

from core.bot import Reverie
from database import db


class Greeting(commands.Cog):
    def __init__(self, bot: Reverie):
        self.bot = bot
        self.db = db.greeting

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        greeting_settings = await self.db.get_settings(member.guild.id)
        if not greeting_settings or not greeting_settings.enabled:
            return

        await greeting_settings.greet(member)

    @app_commands.command(name='greet', description='Статус приветствий для новых участников')
    @app_commands.default_permissions(administrator=True)
    async def greet_status(self, interaction: discord.Interaction):
        settings = await self.db.get_settings(interaction.guild.id)

        status = 'включено' if settings.enabled else 'выключено'
        dm_status = 'включено' if settings.dm_enabled else 'выключено'

        embed = discord.Embed(
            title='### Статус приветствий',
            description=(
                f'Приветствие в гильдии: {status}\n'
                f'Приветствие в ЛС: {dm_status}\n'
                f'Сообщение приветствия в гильдии: {settings.guild_message}\n'
                f'Сообщение приветствия в ЛС: {settings.dm_message}'
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    dm_group = app_commands.Group(
        name='dm-greet',
        description='Управление приветствиями для новых участников в ЛС',
        guild_only=True
    )

    @dm_group.command(name='toggle', description='Включить/выключить приветствие в ЛС')
    @app_commands.default_permissions(administrator=True)
    async def toggle_dm_greet(self, interaction: discord.Interaction):
        settings = await self.db.get_settings(interaction.guild.id)

        settings.dm_enabled = not settings.dm_enabled
        await self.db.set_enabled(interaction.guild.id, "dm", settings.dm_enabled)

        status = 'включено' if settings.enabled else 'выключено'
        await interaction.response.send_message(f'### Приветствие в ЛС {status}.', ephemeral=True)

    @dm_group.command(name='set-message', description='Установить сообщение приветствия в ЛС')
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message='Сообщение приветствия')
    async def set_dm_greet_message(self, interaction: discord.Interaction, message: str):
        settings = await self.db.get_settings(interaction.guild.id)

        settings.dm_message = message
        await self.db.set_text(interaction.guild.id, message, "dm")

        await interaction.response.send_message('### Сообщение приветствия в ЛС обновлено.', ephemeral=True)

    guild_group = app_commands.Group(
        name='guild-greet',
        description='Управление приветствиями для новых участников в гильдии',
        guild_only=True
    )

    @guild_group.command(name='toggle', description='Включить/выключить приветствие в гильдии')
    @app_commands.default_permissions(administrator=True)
    async def toggle_guild_greet(self, interaction: discord.Interaction):
        settings = await self.db.get_settings(interaction.guild.id)

        settings.enabled = not settings.enabled
        await self.db.set_enabled(interaction.guild.id, "channel", settings.enabled)

        status = 'включено' if settings.enabled else 'выключено'
        await interaction.response.send_message(f'### Приветствие в гильдии {status}.', ephemeral=True)

    @guild_group.command(name='set-message', description='Установить сообщение приветствия в гильдии')
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message='Сообщение приветствия')
    async def set_guild_greet_message(self, interaction: discord.Interaction, message: str):
        settings = await self.db.get_settings(interaction.guild.id)

        settings.guild_message = message
        await self.db.set_text(interaction.guild.id, message, "channel")

        await interaction.response.send_message('### Сообщение приветствия в гильдии обновлено.', ephemeral=True)

    @guild_group.command(name='set-channel', description='Установить канал для приветствий в гильдии')
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel='Канал для приветствий')
    async def set_guild_greet_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        settings = await self.db.get_settings(interaction.guild.id)

        settings.channel_id = channel.id
        await self.db.set_channel(interaction.guild.id, channel.id)

        await interaction.response.send_message(f'### Канал для приветствий установлен: {channel.mention}.',
                                                ephemeral=True)


async def setup(bot: Reverie):
    await bot.add_cog(Greeting(bot))
