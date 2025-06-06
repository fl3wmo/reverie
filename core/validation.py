import functools
import re

from core import security


def user_id(user: str) -> int:
    if result := re.search(r'(\d+)', user):
        return int(result.group(1))
    raise ValueError('Неверный формат пользователя.')

_nickname_regex = re.compile(r'^[A-Z][a-z]+ ([A-Z][a-z]+ ?)?[A-Z][a-z]+$')
def nickname(nickname: str) -> str:
    if not _nickname_regex.match(nickname):
        raise ValueError("Никнейм должен быть в формате 'Name Surname'.")
    return nickname

def parse_duration(duration: str, default_unit: str) -> int:
    match = re.match(r"^(\d+)([смчд]?)$", duration)
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


def duration_formatter(default_unit: str = 'м'):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction, user, duration, reason, *args, **kwargs):
            try:
                if duration.strip() == '-1' and default_unit == 'д':
                    duration_in_seconds = None
                else:
                    duration_in_seconds = parse_duration(duration, default_unit)
            except ValueError as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            max_duration = (86400 * 30) if default_unit == 'д' else (86400 * 14)
            if security.user_level(interaction.user) >= security.PermissionLevel.GMD:
                max_duration *= 10
            if duration_in_seconds and duration_in_seconds > max_duration:
                await interaction.response.send_message(
                    f"Максимальная длительность наказания — {max_duration // 86400} дн.",
                    ephemeral=True
                )
                return
            return await func(self, interaction, user, duration_in_seconds, reason, *args, **kwargs)

        return wrapper

    return decorator
