import functools

import discord

_moderator_levels = {
    1: ('MD', "Модератор"),
    2: ('SMD', "Ст. Модератор"),
    3: ('AD', "Ассистент Discord"),
    4: ('GMD', "Главный Модератор"),
    5: ('DS', "Следящий за Discord")
}


def _moderator_info(user: discord.Member | discord.User) -> tuple[int, tuple[str, str]]:
    if isinstance(user, discord.User):
        return 0, ('', '')

    for level, moderator_role in reversed(_moderator_levels.items()):
        if any(moderator_role[1] in role.name for role in user.roles):
            return level, moderator_role
    
    return 0, ('', '')


def user_permissions_compare(user1: discord.Member, user2: discord.Member | discord.User) -> None:
    if not isinstance(user2, discord.Member):
        return

    if user1.top_role <= user2.top_role:
        raise ValueError('У вас нет прав чтобы выполнить это действие на этом пользователе.')


def user_level(user: discord.Member | discord.User) -> int:
    return _moderator_info(user)[0]


def user_tag(user: discord.Member | discord.User) -> str:
    return _moderator_info(user)[1][0]


def restricted(level: int):
    def wrapper(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            user = args[1].user
            if user_level(user) < level:
                raise ValueError('У вас нет прав для выполнения этой команды.')
            return await func(*args, **kwargs)
        return inner
    return wrapper
