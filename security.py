import enum
import functools

import discord

from templates import on_tree_error


class PermissionLevel(enum.IntEnum):
    MD = 1
    SMD = 2
    AD = 3
    GMD = 4
    DS = 5
    CUR = 7


_moderator_levels = {
    1: ('MD', "Модератор"),
    2: ('SMD', "Ст. Модератор"),
    3: ('AD', "Ассистент Discord"),
    4: ('GMD', "Главный Модератор"),
    5: ('DS', "Следящий за Discord"),
    6: ('DS+', '△'),
    7: ('RKN', "Руководитель направления D"),
    8: ('K+', "Руководство Discord")
}


def _moderator_info(user: discord.Member | discord.User) -> tuple[int, tuple[str, str]]:
    if isinstance(user, discord.User):
        return 0, ('', '')

    for level, moderator_role in reversed(_moderator_levels.items()):
        if any(moderator_role[1] in role.name for role in user.roles):
            return level, moderator_role

    if user.guild_permissions.administrator:
        return 8, ('A+', 'Суперпользователь')

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

def user_role(user: discord.Member | discord.User) -> str:
    return _moderator_info(user)[1][1]

def reviewers(guild: discord.Guild) -> list[discord.Role]:
    roles = []
    for role in guild.roles:
        for level, moderator_role in _moderator_levels.items():
            if level in [PermissionLevel.GMD, PermissionLevel.DS] and moderator_role[1] in role.name:
                roles.append(role)
    return roles

def role_checker(guild: discord.Guild) -> discord.Role:
    for role in guild.roles:
        for level, moderator_role in _moderator_levels.items():
            if level == PermissionLevel.SMD and moderator_role[1] in role.name:
                return role

def moderation_team(guild: discord.Guild) -> list[discord.Role]:
    roles = []
    for role in guild.roles:
        for level, moderator_role in _moderator_levels.items():
            if level in [PermissionLevel.MD, PermissionLevel.SMD, PermissionLevel.AD] and moderator_role[1] in role.name:
                roles.append(role)
    return roles

def administration(guild: discord.Guild) -> discord.Role | None:
    for role in guild.roles:
        if role.name.lower().endswith('администратор'):
            return role
    return None

def head_moderation_team(guild: discord.Guild) -> discord.Role:
    for role in guild.roles:
        if 'Discord™' in role.name:
            return role
    raise ValueError('Не найдена роль Discord™')

def is_in_head_moderation_team(user: discord.User, guilds: list[discord.Guild]) -> bool:
    for guild in guilds:
        try:
            role = head_moderation_team(guild)
        except ValueError:
            continue
        if role in user.roles:
            return True
    return False

def restricted(level: PermissionLevel):
    def wrapper(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            interaction = args[1]
            user = interaction.user
            if user_level(user) < level:
                if interaction.type == discord.InteractionType.component:
                    return await on_tree_error(interaction, 'У вас нет прав для выполнения этой команды.')
                raise ValueError('У вас нет прав для выполнения этой команды.')
            return await func(*args, **kwargs)
        return inner
    return wrapper
