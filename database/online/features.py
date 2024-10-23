import datetime

import discord


def is_counting(channel: discord.VoiceChannel) -> bool:
    if "вопрос" in channel.name.lower() or "общение" in channel.name.lower():
        if channel.user_limit > 2 or not channel.user_limit:
            if (
                    channel.overwrites_for(channel.guild.default_role).connect is not False and
                    channel.overwrites_for(channel.guild.default_role).view_channel is not False
            ):
                return True
    return False


def get_dict_of_time_intervals(start_date, end_date):
    delta = end_date - start_date
    result = {}
    current_date = start_date.date()
    while current_date <= end_date.date():
        if current_date == start_date.date() == end_date.date():
            seconds_in_date = delta.total_seconds()
        elif current_date == start_date.date():
            seconds_in_date = (
                    datetime.datetime.combine(current_date, datetime.datetime.max.time()) - start_date
            ).total_seconds()
        elif current_date == end_date.date():
            seconds_in_date = (
                    end_date - datetime.datetime.combine(current_date, datetime.datetime.min.time())
            ).total_seconds()
        else:
            seconds_in_date = 24 * 3600
        result[current_date.strftime('%d.%m.%Y')] = seconds_in_date
        current_date += datetime.timedelta(days=1)
    return result


def mashup_info(all_online, current_online, date):
    join_time = datetime.datetime.strptime(current_online['join_time'], '%Y-%m-%d %H:%M:%S')
    seconds = get_dict_of_time_intervals(join_time, datetime.datetime.now()).get(date, 0)
    if seconds == 0:
        return all_online

    for row in all_online:
        if row['channel_id'] == current_online['channel_id']:
            row['seconds'] += seconds
            break
    else:
        all_online.append({
            "user_id": current_online['user_id'],
            "guild_id": current_online['guild_id'],
            "channel_id": current_online['channel_id'],
            "channel_name": current_online['channel_name'],
            "date": date,
            "seconds": seconds,
            "is_counting": current_online['is_counting']
        })
    return all_online


def is_date_valid(date: str):
    try:
        datetime.datetime.strptime(date, '%d.%m.%Y')
        return True
    except ValueError:
        return False


def date_range(start_datetime, end_datetime):
    date_format = "%d.%m.%Y"

    current_datetime = start_datetime
    dates = []

    while current_datetime <= end_datetime:
        dates.append(current_datetime.strftime(date_format))
        current_datetime += datetime.timedelta(days=1)

    return dates


def seconds_to_time(seconds: int) -> str:
    seconds = round(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"
