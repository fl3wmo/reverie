import datetime
import re
import functools

import discord

import security


_action_types = {
    'ban': 'Бан',
    'kick': 'Кик',
    'mute': 'Мут',
    'warn': 'Варн',
    'hide': 'Хайд'
}

_action_notes = {
    'give': "Выдача: ",
    'remove': "Снятие: ",
    'full': "Полный",
    'voice': "Голосовой",
    'text': "Текстовый",
    'global': "Глобальный",
    'temp': "Временный",
    'approve': "Одобрение",
    'reject': "Отклонение",
}


def action(action_type: str) -> str:
    result = [name for template_note_type, name in _action_notes.items() if template_note_type in action_type]
    result += [name for template_action_type, name in _action_types.items() if template_action_type in action_type]
    return ' '.join(result).capitalize()


def user(obj: discord.Member | discord.User) -> str:
    result = obj.mention
    if tag := security.user_tag(obj):
        result += f' ({tag})'
    return result


def time(seconds: float | None) -> str:
    if seconds is None:
        return 'Навсегда'
    
    if seconds < 60:
        return f'{seconds} сек.'
    elif seconds < 3600:
        return f'{seconds // 60} мин.'
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч. {minutes} мин."
    return f"{seconds // 86400} дн."


def date(obj: datetime.datetime) -> str:
    return f'<t:{int(obj.astimezone(datetime.UTC).timestamp())}:f>'


def link(obj: str, alias: str = 'Ссылка') -> str:
    return f'[{alias}]({obj})'


_mention_regex = re.compile(r'<@!?(\d+)>')


def embed_mentions(embed: discord.Embed) -> str:
    all_text = ''
    
    if embed.description:
        all_text += embed.description
        
    if embed.fields:
        for field in embed.fields:
            if not field.value:
                continue
            all_text += field.value
    groups = _mention_regex.findall(all_text)
    return '-# ||' + ', '.join([f'<@{m}>' for m in groups]) + '||'


async def link_action(interaction: discord.Interaction, act, **objects) -> None:
    message = await act.log(interaction.guild, **objects)
    await interaction.response.send_message(
        f'## 🥳 Успех!\n[Действие]({message.jump_url}) успешно выполнено.',
        ephemeral=True
    )


def parse_duration(duration: str, default_unit: str) -> int:
    match = re.match(r"^(\d+)([сmчд]?)$", duration)
    if not match:
        raise ValueError("Неправильный формат длительности. Используйте 1с, 1м, 1ч.\n"
                         "Также можно использовать число без единицы для секунд.")

    value, unit = int(match.group(1)), match.group(2) or default_unit
    if unit == 'с':
        return value
    elif unit == 'м':
        return value * 60
    elif unit == 'ч':
        return value * 3600
    elif unit == 'д':
        return value * 86400
    else:
        raise ValueError("Неизвестная единица времени.")


def duration_formatter(default_unit: str = 'с'):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction, user, duration, reason, *args, **kwargs):
            try:
                duration_in_seconds = parse_duration(duration, default_unit)
            except ValueError as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            return await func(self, interaction, user, duration_in_seconds, reason, *args, **kwargs)

        return wrapper

    return decorator