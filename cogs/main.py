import logging
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Reverie


class MainCog(commands.Cog):
    def __init__(self, bot: Reverie):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f'Logged in as {self.bot.user.name}')
        
        info = await self.bot.tree.sync()
        for command in info:
            if command.guild_id is None:
                self.bot.command_ids[command.name] = command.id


async def setup(bot: Reverie):
    await bot.add_cog(MainCog(bot))
