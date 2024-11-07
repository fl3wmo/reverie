import re
import base64

import discord
from discord import Interaction
from discord._types import ClientT

from database import db
from features import find_channel_by_name
from templates import on_tree_error
import templates


def int_to_base64(num):
    num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
    encoded = base64.b64encode(num_bytes).decode('utf-8')
    return encoded

def base64_to_int(encoded):
    num_bytes = base64.b64decode(encoded)
    num = int.from_bytes(num_bytes, byteorder='big')
    return num


async def expiration_notification(bot, notification):
    guild = bot.get_guild(notification.guild)
    notification_channel = find_channel_by_name(guild, 'предупреждения', 'warning')

    embed = discord.Embed(
        title='⌛ Время вышло', color=discord.Color.light_embed(),
        description=f'Уважаемый {templates.user(notification.user)}, вы не успели исправить нарушение в профиле.\nВ скором времени вам будет выдано наказание.',
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text='Время уведомления')

    await notification_channel.send(embed=embed, reference=await notification_channel.fetch_message(notification.message_id))


class SendNotification(discord.ui.DynamicItem[discord.ui.Button], template='notifications:send:(?P<notification_id>[0-9]+)'):
    def __init__(self, notification) -> None:
        super().__init__(
            discord.ui.Button(
                label='Уведомить пользователя (нажимать если не сменил)',
                style=discord.ButtonStyle.secondary,
                custom_id=f'notifications:send:{notification.id}'
            )
        )
        self.notification = notification

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        notification_id = match.group('notification_id')
        notification = await db.notifications.get_by_id(int(notification_id))
        return cls(notification)

    async def callback(self, interaction: Interaction[ClientT]):
        if interaction.user.id != self.notification.moderator:
            return await on_tree_error(interaction, 'Это не ваше.')
        await db.notifications.notify(self.notification)
        embed = interaction.message.embeds[0]
        embed.add_field(name='Статус: Не сменил', value=f'Оповещение об истечении времени отправлено в {templates.date(discord.utils.utcnow(), date_format="f")}', inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        await expiration_notification(interaction.client, self.notification)

def send_notification(notification) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(SendNotification(notification))
    return view
