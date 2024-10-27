import datetime

import discord
from discord import app_commands


async def date(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    dates = [datetime.datetime.now() - datetime.timedelta(days=i) for i in range(7)]
    if current.strip():
        found_dates = [_date for _date in dates if current in _date.strftime('%d.%m.%Y')]
        dates = found_dates or dates

    def description(_date: datetime.datetime) -> str:
        if _date.date() == datetime.datetime.now().date():
            return ' (Сегодня)'
        if _date.date() == (datetime.datetime.now() - datetime.timedelta(days=1)).date():
            return ' (Вчера)'
        return ''

    return [app_commands.Choice(name=_date.strftime('%d.%m.%Y') + description(_date), value=_date.strftime('%d.%m.%Y')) for _date in dates]
