import discord

forum_link = 'https://forum.radmir.games'


class ForumLink(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                url=forum_link + '/forums/422/',
                emoji='📝', label="Подать жалобу"
            )
        )
