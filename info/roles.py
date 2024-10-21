class RoleInfo:
    def __init__(self, role_names, tag, rangs):
        self.role_names = role_names
        self.tag = tag
        self.rangs = rangs

    def find(self, guild_roles):
        for role in guild_roles:
            if role.name.lower() in [r.lower() for r in self.role_names]:
                return role
        return None

    def rang_name(self, num):
        return self.rangs[num - 1]

    def form_nickname(self, rang: int, nickname: str) -> str:
        return f'[{self.tag.format(rang)}] {nickname}'

    async def give(self, member, nickname: str, rang: int):
        role = self.find(member.guild.roles)
        if role:
            await member.add_roles(role)
        await member.edit(nick=self.form_nickname(rang, nickname))

    async def remove(self, member):
        role = self.find(member.roles)
        if role:
            await member.remove_roles(role)
        await member.edit(nick=None)

role_info = {
    'Правительство': RoleInfo(['・Правительство', '・Пра-во'], 'Пра-во | {}',
                              ["Водитель", "Охранник", "Нач.Охраны", "Секретарь", "Старший секретарь", "Лицензёр",
                               "Адвокат", "Депутат"]),
    'Министерство Обороны': RoleInfo(['・Министерство Обороны', '・МО'], 'МО | {}',
                                     ["Рядовой", "Ефрейтор", "Сержант", "Прапорщик", "Лейтенант", "Капитан", "Майор",
                                      "Подполковник"]),
    'Министерство Здравоохранения': RoleInfo(['・Министерство Здравоохранения', '・МЗ'], 'МЗ | {}',
                                             ["Интерн", "Фельдшер", "Участковый врач", "Терапевт", "Проктолог",
                                              "Нарколог", "Хирург", "Заведующий отделением"]),
    'Теле-Радио Компания «Ритм»': RoleInfo(['・ТРК "Ритм"', '・ТРК'], 'ТРК | {}',
                                           ["Стажёр", "Светотехник", "Монтажёр", "Оператор", "Дизайнер", "Репортер",
                                            "Ведущий", "Режиссёр"]),
    'Министерство Внутренних Дел': RoleInfo(['・Министерство Внутренних Дел', '・МВД'], 'МВД | {}',
                                            ["Рядовой", "Сержант", "Старшина", "Прапорщик", "Лейтенант", "Капитан",
                                             "Майор", "Подполковник"]),
    'Министерство Чрезвычайных Ситуаций': RoleInfo(['・Министерство Чрезвычайных Ситуаций', '・МЧС'], 'МЧС | {}',
                                                   ["Рядовой", "Сержант", "Старшина", "Прапорщик", "Лейтенант",
                                                    "Капитан",
                                                    "Майор", "Подполковник"]),
    'Федеральная Служба Исполнения Наказаний': RoleInfo(['・Федеральная Служба Исполнения Наказаний', '・ФСИН'],
                                                        'ФСИН | {}',
                                                        ["Охранник", "Конвоир", "Надзиратель", "Инспектор"])
}


def find_role(role_name):
    for key, info in role_info.items():
        if role_name in info.role_names:
            return info
    return None
