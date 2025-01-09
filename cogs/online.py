import datetime
import json

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


import security
import templates
from bot import EsBot
from buttons.online import online_reload
import autocompletes
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


class OnlineCog(commands.Cog):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.online
        self.hassle_data: dict[str, None | dict | datetime.datetime] = {'last_update': None, 'data': None}

    @app_commands.command(name='online', description='Показать онлайн пользователя')
    @app_commands.rename(user='пользователь', date='дата', is_open='открытые-каналы')
    @app_commands.describe(
        user='Пользователь, чей онлайн вы хотите проверить',
        date='Дата в формате dd.mm.YYYY',
        is_open='Подсчитывать онлайн только в открытых каналах.'
    )
    @app_commands.autocomplete(date=autocompletes.date)
    async def online(self, interaction: discord.Interaction,
                     user: discord.Member,
                     date: str,
                     is_open: bool):
        if not date:
            date = datetime.datetime.now().strftime('%d.%m.%Y')
        elif not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        date = datetime.datetime.strptime(date, '%d.%m.%Y').strftime('%Y-%m-%d')
        if not user:
            user = interaction.user

        if security.user_level(interaction.user) < security.PermissionLevel.MD and user.id != interaction.user.id:
            raise ValueError('Вы не можете просматривать онлайн других пользователей.')
        
        info = await self.db.get_info(is_open, user_id=user.id, guild_id=interaction.guild.id, date=date)
        await interaction.response.send_message(embed=info.to_embed(user.id, is_open, date), view=online_reload(user.id, interaction.user.id, interaction.guild.id, is_open, date))

    @app_commands.command(name='week-online', description='Показать онлайн пользователя за неделю')
    @app_commands.rename(user='пользователь', week='неделя')
    @app_commands.describe(user='Пользователь, чей онлайн вы хотите проверить', week='Текущая или прошлая неделя')
    @app_commands.choices(week=[app_commands.Choice(name='Текущая', value='Текущая'), app_commands.Choice(name='Прошлая', value='Прошлая')])
    @app_commands.default_permissions(manage_nicknames=True)
    async def week_online(self, interaction: discord.Interaction, week: app_commands.Choice[str], user: discord.Member = None):
        today = datetime.datetime.now()
        user = user or interaction.user
        if week.value == 'Текущая':
            start_date = today - datetime.timedelta(days=today.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif week.value == 'Прошлая':
            start_date = today - datetime.timedelta(days=today.weekday() + 7)
            end_date = start_date + datetime.timedelta(days=6)
        else:
            raise ValueError("Invalid week option.")

        online = await self.db.get_diapason_info(user_id=user.id, guild_id=interaction.guild.id, date_from=start_date, date_to=end_date, is_open=True)
        embed = discord.Embed(title=f'⏱️ Статистика за неделю',
                                color=discord.Color.light_embed(), timestamp=discord.utils.utcnow())
        embed.set_footer(text='Информация обновлена')
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        total_online = sum(info.total_seconds for info in online.values())

        embed.add_field(name='Пользователь', value=user.mention, inline=False)
        embed.add_field(name='Неделя', value=f'{week.name}\n-# ({start_date.strftime("%d.%m")} - {end_date.strftime("%d.%m")})', inline=True)
        embed.add_field(name='Общее время', value=templates.time(total_online, display_hour=True), inline=True)
        embed.add_field(name='По датам', value='\n'.join(f'{datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")}: {templates.time(info.total_seconds, display_hour=True)}' for date, info in online.items()) or 'Нет активности.', inline=False)

        channels = {}
        for info in online.values():
            for channel in info.channels:
                if channel.channel_name not in channels:
                    channels[channel.channel_name] = 0
                channels[channel.channel_name] += channel.seconds

        embed.add_field(name='По каналам', value='\n'.join(f'{channel}: {templates.time(seconds, display_hour=True)}' for channel, seconds in channels.items()) or 'Нет активности.', inline=False)
        await interaction.response.send_message(content=templates.embed_mentions(embed), embed=embed, ephemeral=True)

    @app_commands.command(name='online-top', description='Показать топ пользователей по онлайну')
    @app_commands.rename(year='год', month='месяц', is_open='открытые-каналы', this_guild='этот-сервер')
    @app_commands.describe(
        year='Год в формате YYYY',
        month='Месяц в формате MM',
        is_open='Подсчитывать онлайн только в открытых каналах.',
        this_guild='Подсчитывать онлайн только на этом сервере.'
    )
    async def online_top(self, interaction: discord.Interaction, year: app_commands.Range[int, 2023, datetime.datetime.now().year], month: app_commands.Range[int, 1, 12], is_open: bool, this_guild: bool = True):
        await interaction.response.defer(ephemeral=True)
        info = await self.db.get_top(year, month, is_open, interaction.guild.id if this_guild else None)
        message = f'### 🏆 Топ по онлайну за {str(month).zfill(2)}.{year}\n'
        for index, (user_id, total_seconds) in enumerate(info.items(), start=1):
            message += f'{index}. <@{user_id}>: {templates.time(total_seconds, display_hour=True)}\n'
        await interaction.followup.send(message, ephemeral=True)

    async def update_hassle_data(self):
        if self.hassle_data['last_update'] and (datetime.datetime.now(datetime.UTC) - self.hassle_data['last_update']).seconds < 60:
            return

        async with aiohttp.ClientSession() as session:
            async with session.get('http://launcher.hassle-games.com:3000/online.json') as response:
                data = await response.json()
                hassle_data = data.get('crmp_new')
                if not hassle_data:
                    raise ValueError('Информация о серверах HASSLE недоступна.')
                self.hassle_data['data'] = hassle_data
                self.hassle_data['last_update'] = datetime.datetime.now(datetime.UTC)

    @app_commands.command(name='hassle', description='Показать онлайн на серверах HASSLE')
    async def hassle(self, interaction: discord.Interaction):
        await self.update_hassle_data()

        embed = discord.Embed(title='🎮 Онлайн на серверах HASSLE', color=discord.Color.light_embed(), timestamp=self.hassle_data['last_update'])
        embed.set_footer(text='Информация обновлена')
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
        for index, online_data in self.hassle_data.get('data').items():
            embed.add_field(name=f'{index}', value=f'{online_data["players"]}/{online_data["maxPlayers"]}', inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='admin-online')
    @app_commands.default_permissions(administrator=True)
    @app_commands.rename(date='дата')
    @app_commands.describe(
        date='Дата в формате dd.mm.YYYY'
    )
    @app_commands.autocomplete(date=autocompletes.date)
    async def admin_online(self, interaction: discord.Interaction, date: str):
        if not is_date_valid(date):
            raise ValueError('Неверный формат даты. Формат: dd.mm.YYYY.\nПример: 07.07.2077')

        date_obj = datetime.datetime.strptime(date, '%d.%m.%Y')
        administrators = security.administration(interaction.guild).members

        stats = {
            admin: await self.db.get_info(is_open=True, user_id=admin.id, guild_id=interaction.guild.id, date=date_obj.strftime('%Y-%m-%d'))
            for admin in administrators
        }

        embed = discord.Embed(
            title=f'🛠️ Статистика за {date}',
            color=discord.Color.light_embed(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text='Информация обновлена')
        embed.set_thumbnail(url='https://i.imgur.com/B1awIXx.png')

        all_info = [f'{index}. {admin.display_name}: {"**" if info.total_seconds else ""}{info.total_time}{"**" if info.total_seconds else ""}'
                    for index, (admin, info) in enumerate(sorted(stats.items(), key=lambda x: x[1].total_seconds, reverse=True))]

        embed.description = '\n'.join(all_info) or 'Нет активности.'

        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            if before.self_deaf != after.self_deaf:
                if after.self_deaf:
                    await self.leave(member, before.channel)
                else:
                    await self.join(member, after.channel)
            return
        if after.self_deaf:
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
            if not member.voice.self_deaf:
                await self.join(member, channel)
        elif prev_channel != channel.id:
            prev_channel_obj = AbstractChannel(_id=prev_channel[0], name=prev_channel[1])
            await self.leave(member, prev_channel_obj)
            if not member.voice.self_deaf:
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
