import asyncio
import datetime
from typing import NamedTuple

import discord
from discord.ext import commands
from discord import app_commands

from buttons.links import ForumLink
from buttons import send_notification
import security
import templates
import validation
from bot import EsBot
from buttons.roles import UnderReviewIndicator
from database import db
from features import Pagination, find_channel_by_name
from info.roles import role_info, RoleInfo
from database.notifications import Notification as NotificationInfo


profile_places: dict[str, str] = {
    'Никнейм': "XtOyFvm",
    'Аватар': 'E80Q7Sy',
    '«Обо мне»': 'YOdiSNd',
    'Местоимение': "i0vaXBO",
    'Статус': 'jzIiiP7',
    'Баннер': '9rbUDfK',
    'Отображаемое имя в профиле': 'xyO9kJF',
    'Юзернейм': 'uk57ZV5',
    'Тег': 'FaL3Bbq',
    'Клантег': 'wN33Gnk'
}

class Notification(commands.Cog):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.notifications
    
    @app_commands.command(name='notify', description='Уведомить пользователя о нарушении в профиле.')
    @app_commands.rename(user='пользователь', content='место')
    @app_commands.describe(user='Пользователь, которому вы хотите отправить уведомление.', content='Место профиля где присутствует нарушение.')
    @app_commands.choices(content=[app_commands.Choice(name=key, value=value) for key, value in profile_places.items()])
    @app_commands.default_permissions(manage_nicknames=True)
    @security.restricted(security.PermissionLevel.MD)
    async def notify(self, interaction: discord.Interaction, user: discord.Member, content: app_commands.Choice[str]):
        notification_channel = find_channel_by_name(interaction.guild, 'предупреждения', 'warning')
        if not notification_channel:
            raise ValueError('Не найден канал для уведомлений.')
        
        add_e = [a for a in content.name if a.isalpha()][-1] == 'е'
        need_lower = [a for a in content.name if a.isalpha()][-1].islower()

        member, user = await self.bot.getch_any(interaction.guild, user.id, interaction.user)
        
        duration = (10 if user.status.value == 'online' else 30) * 60

        embed = discord.Embed(
            title='🚨 Предупреждение!',
            description=(
                f'Уважаемый пользователь, в вашем профиле найдено нарушение.\n'
                f'### Немедленно измените ваш{"е" if add_e else ""} {content.name.lower() if need_lower else content.name}.\n'
                f'В случае, если вы не согласны с действиями модератора, вы можете подать жалобу на [форум проекта](https://forum.radmir.games).'
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(name='Пользователь', value=user.mention)
        embed.add_field(name='Модератор', value=interaction.user.mention)
        embed.add_field(name='Время на смену', value=f'{duration // 60} мин.')
        embed.add_field(name='Что нужно изменить?', value=f'Вам нужно изменить [{content.name}](https://imgur.com/{content.value}.png).\nЕсли вы не знаете что это - нажмите на название, и вы увидите пример.')
        embed.set_footer(text='Время отправки уведомления')

        notification_message = await notification_channel.send(templates.embed_mentions(embed), embed=embed, view=ForumLink())

        await self.db.give(user=user.id, message_id=notification_message.id, guild=interaction.guild.id, moderator=interaction.user.id, notification_type=content.name, duration=duration)

        await interaction.response.send_message(f"## 🥳 Успех!\n[Действие]({notification_message.jump_url}) успешно выполнено.\n\n"
                                        f"По прошествии `{duration // 60} мин.` вам в личные сообщения придёт уведомление.", ephemeral=True)

    @commands.Cog.listener()
    async def on_connect(self):
        self.db.set_callback(self.on_notification_expiration)
        await self.db.load()

    async def on_notification_expiration(self, notification: NotificationInfo):
        await self.bot.wait_until_ready()

        guild = self.bot.get_guild(notification.guild)
        moderator = await self.bot.getch_user(notification.moderator)
        if not moderator:
            return

        embed = discord.Embed(
            title='⌛ Время вышло', color=discord.Color.light_embed(),
            description=f'У пользователя вышло время на смену информации.\nПроверьте, изменил ли он её, и если нет - уведомите, и выдайте наказание.',
            timestamp=discord.utils.utcnow()
        )

        embed.set_author(name=f'Уведомление из: {guild.name}', icon_url=guild.icon.url)
        embed.add_field(name='Пользователь', value=templates.user(notification.user))
        embed.set_footer(text='Время отправки уведомления')

        channel = find_channel_by_name(guild, "чат-модерации", "чат-модераторов")
        try:
            await moderator.send(templates.embed_mentions(embed), embed=embed, view=send_notification(notification))
        except discord.Forbidden:
            await channel.send(
                f'{templates.embed_mentions(embed)}\n-# {moderator.mention}, '
                f'оповещения будут приходить в ЛС если вы откроете ЛС с ботом.',
                embed=embed, view=send_notification(notification)
            )

async def setup(bot: EsBot):
    await bot.add_cog(Notification(bot))
