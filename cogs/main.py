import logging

import discord
from discord.ext import commands

from core.bot import Reverie


class MainCog(commands.Cog):
    def __init__(self, bot: Reverie):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f'Logged in as {self.bot.user.name}')
        
        info = await self.bot.tree.sync()
        await self.bot.change_presence(
            activity=discord.CustomActivity(name='максимум сваги', emoji='✨'),
            status=discord.Status.do_not_disturb
        )

        for command in info:
            if command.guild_id is None:
                self.bot.command_ids[command.name] = command.id


async def setup(bot: Reverie):
    await bot.add_cog(MainCog(bot))
