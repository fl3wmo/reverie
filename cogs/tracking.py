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
from database.roles.request import RoleRequest


def stringify_actions(actions):
    return '\n・ '.join(
            [f'{templates.action(action_type, short=True)}: `{len(acts)}`' for action_type, acts in
             sorted(actions.items(), key=lambda x: len(x[1]), reverse=True)])

def stringify_roles(roles: dict[str, list[RoleRequest]]):
    return '\n・ '.join(
        sorted([f'{role}: `{len(acts)}`' for role, acts in
         sorted(roles.items(), key=lambda x: len(x[1]), reverse=True)]))

def plural_items(n, items):
    if n % 10 == 1 and n % 100 != 11:
        p = 0
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        p = 1
    else:
        p = 2

    return f'**{n}** {items[p]}'

class TrackingCog(commands.GroupCog, name='tracking'):
    def __init__(self, bot: EsBot):
        self.bot = bot

    async def send_action_stats(self, interaction, user, date, is_moderator=False, moderator=None):
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        if not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        date_obj = datetime.datetime.strptime(date, '%d.%m.%Y')

        punishments = await db.actions.by_moderator(moderator.id, counting=True, guild=interaction.guild.id,
                                                    date_from=date_obj, date_to=date_obj + datetime.timedelta(days=7))
        roles = await db.roles.moderator_work(moderator=moderator.id, guild=interaction.guild.id, date_from=date_obj)
        online = await db.online.get_info(is_open=True, user_id=moderator.id, guild_id=interaction.guild.id,
                                          date=date)

        punishments_dict = {}
        for action in punishments:
            punishments_dict.setdefault(action.type, []).append(action)

        roles_dict = {}
        for role in roles:
            roles_dict.setdefault('Одобрено' if role.approved else 'Отклонено', []).append(role)

        punishments_info = stringify_actions(punishments_dict) or 'Нет наказаний'
        roles_info = stringify_roles(roles_dict) or 'Нет действий'

        # Create embed
        embed = discord.Embed(description=f'### 🛠️ Действия {moderator.mention if is_moderator else user.mention}',
                              color=discord.Color.light_embed(), timestamp=discord.utils.utcnow())
        embed.add_field(name='Норма', value=f'`☠️` {plural_items(sum(len(v) for v in punishments_dict.values()), ('наказание', 'наказания', 'наказаний'))}\n'
                                            f'`🎭` {plural_items(len(roles_dict.get("Одобрено", [])), ('роль', 'роли', 'ролей'))}\n'
                                            f'`⏱️` **{templates.time(online.total_seconds)}**', inline=True)
        embed.add_field(name='Дата', value=date, inline=True)
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        embed.add_field(name='Наказания', value='・ ' + punishments_info, inline=False)
        embed.add_field(name='Роли', value='・ ' + roles_info, inline=False)
        embed.set_footer(text="Информация обновлена")

        await interaction.response.send_message(content=templates.embed_mentions(embed), embed=embed, ephemeral=True)

    @app_commands.command(name='my', description='Посмотреть свою статистику')
    @app_commands.rename(date='дата')
    @app_commands.describe(date='Дата в формате dd.mm.YYYY')
    @app_commands.autocomplete(date=autocompletes.date)
    @security.restricted(security.PermissionLevel.MD)
    async def my(self, interaction: discord.Interaction, date: str = None):
        await self.send_action_stats(interaction, interaction.user, date, is_moderator=True, moderator=interaction.user)

    @app_commands.command(name='moderator', description='Посмотреть действия модератора')
    @app_commands.rename(moderator='модератор', date='дата')
    @app_commands.describe(moderator='Модератор, действия которого нужно посмотреть', date='Дата в формате dd.mm.YYYY')
    @app_commands.autocomplete(date=autocompletes.date)
    @security.restricted(security.PermissionLevel.GMD)
    async def moderator(self, interaction: discord.Interaction, moderator: discord.Member, date: str = None):
        await self.send_action_stats(interaction, interaction.user, date, is_moderator=True, moderator=moderator)

    @app_commands.command(name='week', description='Посмотреть статистику за неделю')
    @app_commands.rename(moderator='модератор', week='неделя')
    @app_commands.describe(moderator='Модератор, действия которого нужно посмотреть', week='Неделя которую нужно посмотреть')
    @app_commands.choices(week=[app_commands.Choice(name='Текущая', value='Текущая'), app_commands.Choice(name='Прошлая', value='Прошлая')])
    @security.restricted(security.PermissionLevel.GMD)
    async def week(self, interaction: discord.Interaction, week: Choice[str], moderator: discord.Member = None):
        moderators = [moderator] if moderator else list(set(member for role in security.moderation_team(interaction.guild) for member in role.members))

        today = datetime.datetime.now()
        if week.value == 'Текущая':
            start_date = today - datetime.timedelta(days=today.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif week.value == 'Прошлая':
            start_date = today - datetime.timedelta(days=today.weekday() + 7)
            end_date = start_date + datetime.timedelta(days=6)
        else:
            raise ValueError("Неверно выбрана неделя.")

        embed = discord.Embed(title=f'📆 Статистика за неделю',
                              color=discord.Color.light_embed(), timestamp=discord.utils.utcnow())
        embed.add_field(name='Неделя', value=f'{week.name}\n-# ({start_date.strftime("%d.%m")} - {end_date.strftime("%d.%m")})', inline=True)
        embed.set_footer(text='Информация обновлена')
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        for moderator in moderators:
            punishments = await db.actions.by_moderator(moderator.id, counting=True, guild=interaction.guild.id,
                                                        date_from=start_date, date_to=end_date)
            roles = await db.roles.moderator_work(moderator=moderator.id, guild=interaction.guild.id, date_from=start_date, date_to=end_date)
            online = await db.online.get_diapason_info(moderator.id, interaction.guild.id, start_date, end_date, True)
            total_online = sum(info.total_seconds for info in online.values())
            punishments_dict = {}
            for action in punishments:
                punishments_dict.setdefault(action.type, []).append(action)

            roles_dict = {}
            for role in roles:
                roles_dict.setdefault('Одобрено' if role.approved else 'Отклонено', []).append(role)

            embed.add_field(name=f'{moderator.display_name}',
                            value=f'`☠️` {plural_items(sum(len(v) for v in punishments_dict.values()), ("наказание", "наказания", "наказаний"))}\n'
                                  f'`🎭` {plural_items(len(roles_dict.get("Одобрено", [])), ("роль", "роли", "ролей"))}\n'
                                  f'`⏱️` **{templates.time(total_online)}**',
                            inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='day', description='Посмотреть статистику за день')
    @app_commands.rename(moderator='модератор', date='дата')
    @app_commands.describe(moderator='Модератор, действия которого нужно посмотреть', date='Дата в формате dd.mm.YYYY')
    @app_commands.autocomplete(date=autocompletes.date)
    @security.restricted(security.PermissionLevel.GMD)
    async def day(self, interaction: discord.Interaction, date: str, moderator: discord.Member = None):
        moderators = [moderator] if moderator else list(set(member for role in security.moderation_team(interaction.guild) for member in role.members))

        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        if not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        date_obj = datetime.datetime.strptime(date, '%d.%m.%Y')

        embed = discord.Embed(title=f'📅 Статистика за {date}',
                              color=discord.Color.light_embed(), timestamp=discord.utils.utcnow())
        embed.set_footer(text='Информация обновлена')
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        for moderator in moderators:
            punishments = await db.actions.by_moderator(moderator.id, counting=True, guild=interaction.guild.id,
                                                        date_from=date_obj)
            roles = await db.roles.moderator_work(moderator=moderator.id, guild=interaction.guild.id, date_from=date_obj)
            online = await db.online.get_info(is_open=True, user_id=moderator.id, guild_id=interaction.guild.id,
                                              date=date_obj.strftime('%Y-%m-%d'))

            punishments_dict = {}
            for action in punishments:
                punishments_dict.setdefault(action.type, []).append(action)

            roles_dict = {}
            for role in roles:
                roles_dict.setdefault('Одобрено' if role.approved else 'Отклонено', []).append(role)

            embed.add_field(name=f'{moderator.display_name}',
                            value=f'`☠️` {plural_items(sum(len(v) for v in punishments_dict.values()), ("наказание", "наказания", "наказаний"))}\n'
                                  f'`🎭` {plural_items(len(roles_dict.get("Одобрено", [])), ("роль", "роли", "ролей"))}\n'
                                  f'`⏱️` **{templates.time(online.total_seconds)}**',
                            inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot: EsBot):
    await bot.add_cog(TrackingCog(bot))
