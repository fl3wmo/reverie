from datetime import datetime, timedelta
from typing import List, NamedTuple, Optional, Dict, Tuple

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import autocompletes
from features import Pagination
import security
import templates
from bot import EsBot
from database.online.features import is_date_valid
from info.tracking.stats import ModeratorStats
from info.tracking.tracker import ModeratorTracker
from info.tracking.formatter import StatsFormatter
from database import db


class ActionInfo(NamedTuple):
    moderator_id: int
    action_text: str

    def to_text(self, index: int) -> str:
        return f"### 🧑‍💼 <@{self.moderator_id}>\n{self.action_text}"


@app_commands.default_permissions(manage_nicknames=True)
@app_commands.guild_only()
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

    @app_commands.command(name='month', description='Посмотреть статистику за месяц')
    @app_commands.rename(moderator='модератор', month='месяц')
    @app_commands.describe(
        moderator='Модератор, действия которого нужно посмотреть',
        month='Месяц в формате mm.YYYY'
    )
    @app_commands.autocomplete(month=autocompletes.month)
    @security.restricted(security.PermissionLevel.GMD)
    async def month(
            self,
            interaction: discord.Interaction,
            month: str,
            moderator: discord.Member
    ):
        if not is_date_valid(month, '%m.%Y'):
            raise ValueError('Неверный формат месяца. Формат: mm.YYYY.\nПример: 07.2077')

        month_obj = datetime.strptime(month, '%m.%Y')
        start_date = month_obj.replace(day=1)
        end_date = (start_date + timedelta(days=33)).replace(day=1) - timedelta(days=1)

        tracker = ModeratorTracker(interaction.guild)
        stats = await tracker.get_stats(moderator.id, start_date, end_date, return_by_dates=True)

        embed = discord.Embed(
            title=f'📆 Статистика за {month}',
            color=discord.Color.light_embed(),
            description=f'### 🛠️ Действия {moderator.mention}\n\n{stats.format_stats()}',
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        embed.set_footer(text='Информация обновлена')
        embed.add_field(name='Общая статистика', value=stats.format_global_stats())

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

    @app_commands.command(name='check', description='Дополнительная проверка')
    @security.restricted(security.PermissionLevel.CUR)
    async def check(self, interaction: discord.Interaction):
        similar_actions = await db.actions.similar(interaction.guild.id)
        if not similar_actions:
            return await interaction.response.send_message('Похожих действий не найдено', ephemeral=True)
        
        # Process and format the data
        formatted_data: List[Tuple[int, ActionInfo]] = []
        moderators = {}
        
        # Group actions by moderator and user
        for action in similar_actions:
            moderators.setdefault(action.moderator, {}).setdefault(action.user, []).append(action)
        
        # Format the data for pagination
        index = 0
        for moderator_id, users in moderators.items():
            action_text = ""
            for user_id, actions in users.items():
                action_text += f"<@{user_id}> ({len(actions)} действий)\n-# Acts: {', '.join(str(a.id) for a in actions)}\n"
            action_info = ActionInfo(
                moderator_id=moderator_id,
                action_text=action_text
            )
            formatted_data.append((index, action_info))
            index += 1
        
        # Create and send paginated view
        paginator = Pagination(
            bot=self.bot,
            interaction=interaction,
            owner=interaction.user,
            data=formatted_data,
            page_size=5,
            embed_title="Похожие действия"
        )
        
        await paginator.send_initial_message()

async def setup(bot: EsBot):
    await bot.add_cog(TrackingCog(bot))