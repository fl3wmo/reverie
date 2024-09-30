import logging
import os

from discord.ext import commands


class EsBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        await self.load_extensions()

    async def load_extensions(self):
        for filename in os.listdir('./cogs'):
            if '__' not in filename:
                filename = filename.replace('.py', '')
                await self.load_extension(f'cogs.{filename}')
                logging.info(f'Loaded {filename}')

    async def on_ready(self):
        await self.tree.sync()
        logging.info('Command tree synced')
