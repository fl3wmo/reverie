import datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot import EsBot
from buttons.online import online_reload
from database import db
from database.online.features import is_counting, is_date_valid
from database.online.general import CurrentInfo


class AbstractChannel:
    def __init__(self, _id: int, name: str) -> None:
        self.id = _id
        self.name = name


class AbstractUser:
    def __init__(self, _id: int, guild: discord.Guild) -> None:
        self.id = _id
        self.guild = guild
        
async def date_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    dates = [datetime.datetime.now() - datetime.timedelta(days=i) for i in range(7)]
    dates = [date for date in dates if current in date.strftime('%d.%m.%Y')]

    def description(date: datetime.datetime) -> str:
        if date.date() == datetime.datetime.now().date():
            return ' (Сегодня)'
        if date.date() == (datetime.datetime.now() - datetime.timedelta(days=1)).date():
            return ' (Вчера)'
        return ''

    return [app_commands.Choice(name=date.strftime('%d.%m.%Y') + description(date), value=date.strftime('%d.%m.%Y')) for date in dates]


class OnlineCog(commands.Cog):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.online

    @app_commands.command()
    @app_commands.rename(user='пользователь', date='дата', is_open='открытые-каналы')
    @app_commands.describe(
        user='Пользователь, чей онлайн вы хотите проверить',
        date='Дата в формате dd.mm.YYYY',
        is_open='Подсчитывать онлайн только в открытых каналах.'
    )
    @app_commands.autocomplete(date=date_autocomplete)
    async def online(self, interaction: discord.Interaction,
                     user: discord.Member,
                     date: str,
                     is_open: bool):
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        elif not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        if not user:
            user = interaction.user
        info = await self.db.get_info(is_open, user_id=user.id, guild_id=interaction.guild.id, date=date)
        await interaction.response.send_message(embed=info.to_embed(user, is_open, date), view=online_reload(user.id, interaction.user.id, interaction.guild.id, is_open, date))

    async def join(self, member: discord.Member, channel: discord.VoiceChannel) -> None:
        await self.db.add_join_info(member, channel, is_counting(channel))

    async def leave(self, member: discord.Member | AbstractUser, channel: discord.VoiceChannel | discord.StageChannel | AbstractChannel) -> None:
        await self.db.add_leave_info(member, channel)

    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState
    ) -> None:
        if before.channel == after.channel:
            return

        if before.channel is None:
            await self.join(member, after.channel)
        elif after.channel is None:
            await self.leave(member, before.channel)
        else:
            await self.leave(member, before.channel)
            await self.join(member, after.channel)

    async def update_member(self, current_info: CurrentInfo, member: discord.Member, channel: discord.VoiceChannel | discord.StageChannel) -> None:
        if not (prev_channel := current_info.in_channel(member.id, channel.guild.id)):
            await self.join(member, channel)
        elif prev_channel != channel.id:
            prev_channel_obj = AbstractChannel(_id=prev_channel[0], name=prev_channel[1])
            await self.leave(member, prev_channel_obj)
            await self.join(member, channel)

    async def update_users(self, current_info: CurrentInfo, channel: discord.VoiceChannel | discord.StageChannel) -> None:
        for member in channel.members:
            await self.update_member(current_info, member, channel)
        for user in current_info.get_channel_users(channel.id):
            if user not in [member.id for member in channel.members]:
                await self.leave(AbstractUser(user, channel.guild), channel)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        current_info = await self.db.get_current_info()
        for channel in self.bot.get_all_channels():
            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                continue
                
            await self.update_users(current_info, channel)


async def setup(bot: EsBot):
    await bot.add_cog(OnlineCog(bot))
