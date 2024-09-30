import os
import logging

from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix='es!')

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')
        logging.info(f'Loaded {filename[:-3]}')

bot.run(os.getenv('DISCORD_TOKEN'))
