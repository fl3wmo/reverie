from datetime import datetime, timedelta
from typing import Optional, Dict

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import autocompletes
import security
import templates
from bot import EsBot
from database.online.features import is_date_valid
from info.tracking.stats import ModeratorStats
from info.tracking.tracker import ModeratorTracker
from info.tracking.formatter import StatsFormatter


class TrackingCog(commands.GroupCog, name='tracking'):
    def __init__(self, bot: EsBot):
        self.bot = bot
        super().__init__()

    async def create_stats_embed(
            self,
            title: str,
            moderator_stats: Dict[discord.Member, ModeratorStats],
            date_info: Optional[str] = None
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=discord.Color.light_embed(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        embed.set_footer(text='Информация обновлена')

        if date_info:
            embed.add_field(name='Дата', value=date_info, inline=True)

        for moderator, stats in moderator_stats.items():
            embed.add_field(
                name=moderator.display_name,
                value=stats.format_stats(),
                inline=False
            )

        return embed

    @app_commands.command(name='my', description='Посмотреть свою статистику')
    @app_commands.rename(date='дата')
    @app_commands.describe(date='Дата в формате dd.mm.YYYY')
    @app_commands.autocomplete(date=autocompletes.date)
    @security.restricted(security.PermissionLevel.MD)
    async def my(self, interaction: discord.Interaction, date: Optional[str] = None):
        await self.show_moderator_stats(interaction, interaction.user, date)

    @app_commands.command(name='moderator', description='Посмотреть действия модератора')
    @app_commands.rename(moderator='модератор', date='дата')
    @app_commands.describe(
        moderator='Модератор, действия которого нужно посмотреть',
        date='Дата в формате dd.mm.YYYY'
    )
    @app_commands.autocomplete(date=autocompletes.date)
    @security.restricted(security.PermissionLevel.GMD)
    async def moderator(
            self,
            interaction: discord.Interaction,
            moderator: discord.Member,
            date: Optional[str] = None
    ):
        await self.show_moderator_stats(interaction, moderator, date)

    async def show_moderator_stats(
            self,
            interaction: discord.Interaction,
            moderator: discord.Member,
            date: Optional[str] = None
    ):
        date = date or datetime.now().strftime('%d.%m.%Y')
        if not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        date_obj = datetime.strptime(date, '%d.%m.%Y')
        tracker = ModeratorTracker(interaction.guild)
        stats = await tracker.get_stats(moderator.id, date_obj)

        embed = discord.Embed(
            description=f'### 🛠️ Действия {moderator.mention}',
            color=discord.Color.light_embed(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='Норма', value=stats.format_stats(), inline=True)
        embed.add_field(name='Дата', value=date, inline=True)
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        embed.add_field(
            name='Наказания',
            value='・ ' + StatsFormatter.format_actions(stats.punishments),
            inline=False
        )
        embed.add_field(
            name='Роли',
            value='・ ' + StatsFormatter.format_roles(stats.roles),
            inline=False
        )
        embed.set_footer(text="Информация обновлена")

        await interaction.response.send_message(
            content=templates.embed_mentions(embed),
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(name='week', description='Посмотреть статистику за неделю')
    @app_commands.rename(moderator='модератор', week='неделя')
    @app_commands.describe(
        moderator='Модератор, действия которого нужно посмотреть',
        week='Неделя которую нужно посмотреть'
    )
    @app_commands.choices(week=[
        Choice(name='Текущая', value='Текущая'),
        Choice(name='Прошлая', value='Прошлая')
    ])
    @security.restricted(security.PermissionLevel.GMD)
    async def week(
            self,
            interaction: discord.Interaction,
            week: Choice[str],
            moderator: Optional[discord.Member] = None
    ):
        today = datetime.now()
        if week.value == 'Текущая':
            start_date = today - timedelta(days=today.weekday())
        elif week.value == 'Прошлая':
            start_date = today - timedelta(days=today.weekday() + 7)
        else:
            raise ValueError("Неверно выбрана неделя.")

        end_date = start_date + timedelta(days=6)
        moderators = ([moderator] if moderator else
                      list(set(member for role in security.moderation_team(interaction.guild)
                               for member in role.members)))

        tracker = ModeratorTracker(interaction.guild)
        stats = {
            mod: await tracker.get_stats(mod.id, start_date, end_date)
            for mod in moderators
        }

        embed = await self.create_stats_embed(
            title='📆 Статистика за неделю',
            moderator_stats=stats,
            date_info=f'{week.name}\n({start_date.strftime("%d.%m")} - {end_date.strftime("%d.%m")})'
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='day', description='Посмотреть статистику за день')
    @app_commands.rename(moderator='модератор', date='дата')
    @app_commands.describe(
        moderator='Модератор, действия которого нужно посмотреть',
        date='Дата в формате dd.mm.YYYY'
    )
    @app_commands.autocomplete(date=autocompletes.date)
    @security.restricted(security.PermissionLevel.GMD)
    async def day(
            self,
            interaction: discord.Interaction,
            date: str,
            moderator: Optional[discord.Member] = None
    ):
        if not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        date_obj = datetime.strptime(date, '%d.%m.%Y')
        moderators = ([moderator] if moderator else
                      list(set(member for role in security.moderation_team(interaction.guild)
                               for member in role.members)))

        tracker = ModeratorTracker(interaction.guild)
        stats = {
            mod: await tracker.get_stats(mod.id, date_obj)
            for mod in moderators
        }

        embed = await self.create_stats_embed(
            title=f'📅 Статистика за {date}',
            moderator_stats=stats
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: EsBot):
    await bot.add_cog(TrackingCog(bot))