import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import buttons
import security
import validation


class EsBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        self.tree.error(on_tree_error)
        self.add_dynamic_items(buttons.ApprovePunishment, buttons.RejectPunishment)
        await self.load_extensions()

    async def load_extensions(self):
        for filename in os.listdir('./cogs'):
            if '__' not in filename:
                filename = filename.replace('.py', '')
                await self.load_extension(f'cogs.{filename}')
                logging.info(f'Loaded {filename}')

    async def on_ready(self):
        try:
            await self.tree.sync()
            logging.info('Command tree synced')
        except Exception as e:
            logging.error(f'Error: {e}')

    @staticmethod
    async def getch_member(guild: discord.Guild, user_id: int) -> discord.Member | None:
        try:
            return guild.get_member(user_id) or await guild.fetch_member(user_id)
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


async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"Команда ещё недоступна! Попробуйте ещё раз через **{error.retry_after:.2f}** сек!",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("У вас нет прав", ephemeral=True)
    elif isinstance(error, app_commands.CommandInvokeError):
        embed = discord.Embed(
            title='💀 Произошла ошибка',
            description=str(error.original),
            color=discord.Color.dark_grey()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logging.warning(f'Error: {error}')
        await interaction.response.send_message("Произошла ошибка", ephemeral=True)
