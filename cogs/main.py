import logging

from discord.ext import commands


class MainCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f'Logged in as {self.bot.user.name}')


def setup(bot: commands.Bot):
    bot.add_cog(MainCog(bot))
