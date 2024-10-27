import datetime

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import autocompletes
import security
import templates
from bot import EsBot
from database import db
from database.online.features import is_date_valid


class TrackingCog(commands.GroupCog, name='tracking'):
    def __init__(self, bot: EsBot):
        self.bot = bot

    @app_commands.command(name='moderator', description='Посмотреть действия модератора')
    @app_commands.rename(moderator='модератор', date='дата')
    @app_commands.describe(moderator='Модератор, действия которого нужно посмотреть', date='Дата в формате dd.mm.YYYY')
    @app_commands.autocomplete(date=autocompletes.date)
    @security.restricted(security.PermissionLevel.GMD)
    async def moderator(self, interaction: discord.Interaction, moderator: discord.Member, date: str = None):
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        if not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        punishments = await db.actions.by_moderator(moderator.id, counting=True, date=datetime.datetime.strptime(date, '%d.%m.%Y'))
        online = await db.online.get_info(is_open=True, user_id=moderator.id, guild_id=interaction.guild.id, date=date)

        actions = {}

        for action in punishments:
            actions.setdefault(action.type, []).append(action)

        string_info = '\n・ '.join([f'{templates.action(action_type, short=True)}: `{len(acts)}`' for action_type, acts in sorted(actions.items(), key=lambda x: len(x[1]), reverse=True)])
        string_info = string_info or 'Нет наказаний'

        embed = discord.Embed(description=f'### 🛠️ Действия {moderator.mention}', color=discord.Color.light_embed(), timestamp=discord.utils.utcnow())
        embed.add_field(name='Норма', value=f'`☠️` **{sum([len(v) for v in actions.values()])}** наказаний\n'
                                            f'`⏱️` **{templates.time(online.total_seconds)}** в voice', inline=True)
        embed.add_field(name='Дата', value=date, inline=True)
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        embed.add_field(name=f'Наказания', value='・ ' + string_info, inline=False)
        embed.set_footer(text="Информация обновлена")

        await interaction.response.send_message(content=templates.embed_mentions(embed), embed=embed, ephemeral=True)

    @app_commands.command(name='week', description='Посмотреть статистику за неделю')
    @app_commands.rename(moderator='модератор', week='неделя')
    @app_commands.describe(moderator='Модератор, действия которого нужно посмотреть', week='Неделя которую нужно посмотреть')
    @security.restricted(security.PermissionLevel.GMD)
    async def week(self, interaction: discord.Interaction, week: Choice[str], moderator: discord.Member = None):
        pass

async def setup(bot: EsBot):
    await bot.add_cog(TrackingCog(bot))
