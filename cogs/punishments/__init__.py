from discord.ext import commands

from cogs.punishments.base import PunishmentsBase


async def setup(bot: commands.Bot):
    await bot.add_cog(PunishmentsBase(bot))
