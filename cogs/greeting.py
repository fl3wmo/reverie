import discord
from discord import app_commands, TextStyle
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
    @app_commands.guild_only()
    async def greet_status(self, interaction: discord.Interaction):
        settings = await self.db.get_settings(interaction.guild.id)

        status = 'включено' if settings.enabled else 'выключено'
        dm_status = 'включено' if settings.dm_enabled else 'выключено'

        embed = discord.Embed(
            title='Статус приветствий',
            description=f'Вы можете управлять приветствиями используя команды `/dm-greet` и `/guild-greet`.',
            color=discord.Color.green()
        )
        embed.add_field(name=f'На сервере ({status})', value=settings.channel_text or 'Не установлено', inline=False)
        embed.add_field(name=f'В ЛС ({dm_status})', value=settings.dm_text or 'Не установлено', inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    dm_group = app_commands.Group(
        name='dm-greet',
        description='Управление приветствиями для новых участников в ЛС',
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True)
    )

    @dm_group.command(name='toggle', description='Включить/выключить приветствие в ЛС')
    @app_commands.default_permissions(administrator=True)
    async def toggle_dm_greet(self, interaction: discord.Interaction):
        settings = await self.db.get_settings(interaction.guild.id)

        settings.dm_enabled = not settings.dm_enabled
        if settings.dm_enabled and not settings.dm_text:
            return await interaction.response.send_message(
                'Пожалуйста, сначала установите сообщение приветствия в ЛС с помощью команды `/dm-greet set-message`.',
                ephemeral=True
            )

        await self.db.set_enabled(interaction.guild.id, "dm", settings.dm_enabled)

        status = 'включено' if settings.dm_enabled else 'выключено'
        await interaction.response.send_message(f'### Приветствие в ЛС {status}.', ephemeral=True)

    @dm_group.command(name='set-message', description='Установить сообщение приветствия в ЛС')
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message='Сообщение приветствия')
    async def set_dm_greet_message(self, interaction: discord.Interaction, message: str):
        settings = await self.db.get_settings(interaction.guild.id)

        modal = discord.ui.Modal(title='Новое сообщение приветствия', timeout=None)
        input_text = discord.ui.TextInput(label='Сообщение приветствия', style=TextStyle.long,
                                          default=settings.channel_text or '')
        modal.add_item(input_text)

        async def modal_callback(modal_interaction: discord.Interaction):
            message = input_text.value

            await self.db.set_text(interaction.guild.id, message, "dm")

            await modal_interaction.response.send_message('### Сообщение приветствия на в ЛС обновлено.',
                                                          ephemeral=True)

        modal.on_submit = modal_callback

        await interaction.response.send_modal(modal)

    guild_group = app_commands.Group(
        name='guild-greet',
        description='Управление приветствиями для новых участников на сервере',
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True)
    )

    @guild_group.command(name='toggle', description='Включить/выключить приветствие на сервере')
    @app_commands.default_permissions(administrator=True)
    async def toggle_guild_greet(self, interaction: discord.Interaction):
        settings = await self.db.get_settings(interaction.guild.id)

        settings.channel_enabled = not settings.channel_enabled
        if settings.channel_enabled and not settings.channel_text:
            return await interaction.response.send_message(
                'Пожалуйста, сначала установите сообщение приветствия на сервере с помощью команды `/guild-greet set-message`.',
                ephemeral=True
            )
        if settings.channel_enabled and not settings.guild_channel:
            return await interaction.response.send_message(
                'Пожалуйста, сначала установите канал для приветствий на сервере с помощью команды `/guild-greet set-channel`.',
                ephemeral=True
            )

        await self.db.set_enabled(interaction.guild.id, "channel", settings.channel_enabled)

        status = 'включено' if settings.channel_enabled else 'выключено'
        await interaction.response.send_message(f'### Приветствие на сервере {status}.', ephemeral=True)

    @guild_group.command(name='set-message', description='Установить сообщение приветствия на сервере')
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message='Сообщение приветствия')
    async def set_guild_greet_message(self, interaction: discord.Interaction):
        settings = await self.db.get_settings(interaction.guild.id)

        modal = discord.ui.Modal(title='Новое сообщение приветствия', timeout=None)
        input_text = discord.ui.TextInput(label='Сообщение приветствия', style=TextStyle.long,
                                          default=settings.channel_text or '')
        modal.add_item(input_text)

        async def modal_callback(modal_interaction: discord.Interaction):
            message = input_text.value

            await self.db.set_text(interaction.guild.id, message, "channel")

            await modal_interaction.response.send_message('### Сообщение приветствия на сервере обновлено.',
                                                          ephemeral=True)

        modal.on_submit = modal_callback

        await interaction.response.send_modal(modal)

    @guild_group.command(name='set-channel', description='Установить канал для приветствий на сервере')
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
