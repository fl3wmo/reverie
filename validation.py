import re


def user_id(user: str) -> int:
    if result := re.search(r'(\d+)', user):
        return int(result.group(1))
    raise ValueError('Неверный формат пользователя.')
