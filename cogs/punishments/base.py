import discord
from discord import app_commands
from discord.ext import commands


class PunishmentsBase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='act', description='Выводит информацию о действии')
    @app_commands.describe(action='Порядковый номер действия для вывода информации')
    @app_commands.rename(action='номер-действия')
    async def act(self, interaction: discord.Interaction, action: int):
        ...


async def setup(bot: commands.Bot):
    print('loaded')
    await bot.add_cog(PunishmentsBase(bot))
