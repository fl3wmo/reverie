import logging
import os

import discord
from dotenv import load_dotenv

from bot import EsBot

logging.basicConfig(level=logging.INFO)

bot = EsBot(command_prefix='es!', intents=discord.Intents.all())

load_dotenv()

if (token := os.getenv('DISCORD_TOKEN')) is None:
    raise EnvironmentError('DISCORD_TOKEN is not set')

bot.run(token)
