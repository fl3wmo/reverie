import os
import logging

import discord
from dotenv import load_dotenv

from bot import EsBot

logging.basicConfig(level=logging.INFO)

bot = EsBot(command_prefix='es!', intents=discord.Intents.all())


load_dotenv()

bot.run(os.getenv('DISCORD_TOKEN'))
