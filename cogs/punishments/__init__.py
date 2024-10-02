from discord.ext import commands

import cogs.punishments.base as base
import cogs.punishments.mutes as mutes


async def setup(bot: commands.Bot):
    cog_list = (base, mutes)
    for cog in cog_list:
        await cog.setup(bot)
