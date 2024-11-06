import datetime
import aiosqlite
import discord

import templates
from database.online.features import get_dict_of_time_intervals, mashup_info, seconds_to_time


class CurrentInfo:
    def __init__(self, current_users) -> None:
        self.current_users = current_users

    def in_channel(self, user_id, guild_id):
        for user in self.current_users:
            if user['user_id'] == user_id and user['guild_id'] == guild_id:
                return user['channel_id'], user['channel_name']
        return False

    def get_channel_users(self, channel_id):
        return [user['user_id'] for user in self.current_users if user['channel_id'] == channel_id]


class ChannelInfo:
    def __init__(self, channel_id, channel_name, seconds, is_counting):
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.seconds = seconds
        self.is_counting = is_counting


class DateInfo:
    def __init__(self, all_online):
        self._total = 0
        self.channels = []
        for row in all_online:
            self._total += row['seconds']
            self.channels.append(ChannelInfo(
                row['channel_id'], row['channel_name'], row['seconds'], row['is_counting']
            ))

    @property
    def total_seconds(self):
        return self._total

    @property
    def total_time(self):
        return seconds_to_time(self._total)

    def __str__(self):
        return '\n'.join([f'{index}. {channel.channel_name}: {seconds_to_time(channel.seconds)}' for index, channel in enumerate(sorted(self.channels, key=lambda c: c.seconds, reverse=True), 1)])

    def to_embed(self, user, is_open, date):
        embed = ((discord.Embed(title=f'⏱️ Онлайн за {datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")}', timestamp=discord.utils.utcnow(),
                                color=discord.Color.light_embed()))
                 .add_field(name="Пользователь", value=templates.user(user), inline=False)
                 .add_field(name='Общее время', value=self.total_time)
                 .add_field(name='Каналы', value='Открытые' if is_open else 'Все')
                 .set_thumbnail(url='https://i.imgur.com/B1awIXx.png')
                 .set_footer(text='Информация обновлена'))

        if self.channels:
            embed.add_field(name='Время в каналах', value=str(self), inline=False)
        return embed

    def to_field(self):
        return {'name': "Время в каналах", 'value': str(self), 'inline': False}

class OnlineDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db = None  # Инициализируем переменную для хранения соединения

    async def init_db(self):
        self.db = await aiosqlite.connect(self.db_path)  # Устанавливаем соединение
        await self.db.execute('''CREATE TABLE IF NOT EXISTS current_online (
                                user_id INTEGER, guild_id INTEGER, channel_id INTEGER, 
                                channel_name TEXT, join_time TEXT, is_counting BOOLEAN)''')
        await self.db.execute('''CREATE TABLE IF NOT EXISTS all_online (
                                user_id INTEGER, guild_id INTEGER, channel_id INTEGER, 
                                channel_name TEXT, date TEXT, seconds INTEGER, is_counting BOOLEAN,
                                UNIQUE(user_id, guild_id, channel_id, date))''')  # Уникальное ограничение добавлено
        await self.db.commit()

    async def close_db(self):
        if self.db is not None:
            await self.db.close()  # Закрываем соединение

    async def get_current_info(self):
        return CurrentInfo(await self.get_current_users())

    async def get_current_users(self):
        cursor = await self.db.execute("SELECT * FROM current_online")
        return [{'user_id': row[0], 'guild_id': row[1], 'channel_id': row[2], 'channel_name': row[3],
                 'join_time': row[4], 'is_counting': row[5]} for row in await cursor.fetchall()]

    async def pop_current_info(self, user_id: int, channel_id: int):
        cursor = await self.db.execute("SELECT * FROM current_online WHERE user_id = ? AND channel_id = ?",
                                        (user_id, channel_id))
        current_info = await cursor.fetchone()
        if not current_info:
            return None
        await self.db.execute("DELETE FROM current_online WHERE user_id = ? AND channel_id = ?",
                             (user_id, channel_id))
        await self.db.commit()
        return {'user_id': current_info[0], 'guild_id': current_info[1], 'channel_id': current_info[2],
                'channel_name': current_info[3], 'join_time': current_info[4], 'is_counting': current_info[5]}

    async def add_join_info(self, member: discord.Member, channel, is_counting: bool):
        await self.db.execute('''INSERT INTO current_online (user_id, guild_id, channel_id, channel_name, 
                            join_time, is_counting) VALUES (?, ?, ?, ?, ?, ?)''',
                             (member.id, member.guild.id, channel.id, channel.name,
                              datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), is_counting))
        await self.db.commit()

    async def add_leave_info(self, member: discord.Member, channel):
        now = datetime.datetime.now()
        current_info = await self.pop_current_info(member.id, channel.id)
        if not current_info:
            return

        intervals: dict[str, int] = get_dict_of_time_intervals(
            datetime.datetime.strptime(current_info['join_time'], '%Y-%m-%d %H:%M:%S'), now)

        for date, seconds in intervals.items():
            await self.db.execute('''INSERT INTO all_online (user_id, guild_id, channel_id, channel_name, date, 
                            seconds, is_counting) 
                            VALUES (?, ?, ?, ?, ?, ?, ?) 
                            ON CONFLICT(user_id, guild_id, channel_id, date) 
                            DO UPDATE SET seconds = seconds + ?, is_counting = ?''',
                                 (member.id, member.guild.id, channel.id, channel.name, date,
                                  seconds, current_info['is_counting'], seconds, current_info['is_counting']))
        await self.db.commit()

    async def get_info(self, is_open: bool, user_id: int, guild_id: int, date: str = None):
        query = "SELECT * FROM all_online WHERE user_id = ? AND guild_id = ?"
        params = [user_id, guild_id]
        if date:
            query += " AND date = ?"
            params.append(date)
        if is_open:
            query += " AND is_counting = ?"
            params.append(is_open)

        cursor = await self.db.execute(query, params)
        all_online = [{'user_id': row[0], 'guild_id': row[1], 'channel_id': row[2], 'channel_name': row[3],
                       'date': row[4], 'seconds': row[5], 'is_counting': row[6]} for row in await cursor.fetchall()]

        query = "SELECT * FROM current_online WHERE user_id = ? AND guild_id = ?"
        params = [user_id, guild_id]
        if is_open:
            query += " AND is_counting = ?"
            params.append(is_open)
        cursor = await self.db.execute(query, params)
        current_online = await cursor.fetchone()

        if current_online:
            all_online = mashup_info(all_online, {
                'user_id': current_online[0], 'guild_id': current_online[1], 'channel_id': current_online[2],
                'channel_name': current_online[3], 'join_time': current_online[4], 'is_counting': current_online[5]
            }, date)
        return DateInfo(all_online)

    async def get_diapason_info(self, user_id: int, guild_id: int, date_from: datetime.datetime, date_to: datetime.datetime, is_open: bool) -> dict[str, DateInfo]:
        query = "SELECT * FROM all_online WHERE user_id = ? AND guild_id = ? AND date BETWEEN ? AND ?"
        params = [user_id, guild_id, date_from.strftime('%Y-%m-%d'), date_to.strftime('%Y-%m-%d')]
        if is_open:
            query += " AND is_counting = ?"
            params.append(is_open)
        cursor = await self.db.execute(query, params)

        all_online = [{'user_id': row[0], 'guild_id': row[1], 'channel_id': row[2], 'channel_name': row[3],
                          'date': row[4], 'seconds': row[5], 'is_counting': row[6]} for row in await cursor.fetchall()]
        dates = {date: [] for date in set(row['date'] for row in all_online)}

        for row in all_online:
            dates[row['date']].append(row)

        if date_to > datetime.datetime.now() > date_from:
            query = "SELECT * FROM current_online WHERE user_id = ? AND guild_id = ?"
            params = [user_id, guild_id]
            if is_open:
                query += " AND is_counting = ?"
                params.append(is_open)
            cursor = await self.db.execute(query, params)
            current_online = await cursor.fetchall()

            for row in current_online:
                dates[datetime.datetime.now().strftime('%Y-%m-%d')] = mashup_info(dates[datetime.datetime.now().strftime('%Y-%m-%d')], {
                    'user_id': row[0], 'guild_id': row[1], 'channel_id': row[2],
                    'channel_name': row[3], 'join_time': row[4], 'is_counting': row[5]
                }, datetime.datetime.now().strftime('%Y-%m-%d'))

        return {date: DateInfo(all_online) for date, all_online in dates.items()}

    async def get_top(self, year: int, month: int, is_open: bool, guild_id: int | None = None):
        start_date = f"{year}-{str(month).zfill(2)}-01"
        end_date = f"{year}-{str(month).zfill(2)}-31"

        query = "SELECT user_id, guild_id, SUM(seconds) as total_seconds FROM all_online WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]
        
        if guild_id:
            query += " AND guild_id = ?"
            params.append(guild_id)
        if is_open:
            query += " AND is_counting = ?"
            params.append(is_open)
        
        query += " GROUP BY user_id, guild_id ORDER BY total_seconds DESC LIMIT 20"
        cursor = await self.db.execute(query, params)
        top = [{'user_id': row[0], 'guild_id': row[1], 'total_seconds': row[2]} for row in await cursor.fetchall()]
        return top

    def __del__(self):
        import asyncio
        asyncio.run(self.close_db())
