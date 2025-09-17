import discord

from config import forum_link


class ForumLink(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                url=forum_link,
                emoji='📝', label="Подать жалобу"
            )
        )
