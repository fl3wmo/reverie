import discord.ui


def sent_from(guild: discord.Guild) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label=f'Из {guild.name}',
            style=discord.ButtonStyle.secondary,
            emoji='📨',
            custom_id=f'sent_from:{guild.id}'
        )
    )
    return view
