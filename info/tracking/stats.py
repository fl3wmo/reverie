import datetime
from dataclasses import dataclass
from typing import Dict, List

import templates
from database.online.features import date_range
from templates import format_plural
from database.roles.request import RoleRequest


@dataclass
class ModeratorStats:
    punishments: Dict[str, List[any]]  # Replace 'any' with actual Action type if available
    roles: Dict[str, List[RoleRequest]]
    online_time: int
    removed_roles: List[any]  # Replace 'any' with actual Role type if available

    @property
    def total_punishments(self) -> int:
        return sum(len(actions) for actions in self.punishments.values())

    @property
    def total_roles(self) -> float:
        return len(self.roles.get("Одобрено", [])) + len(self.removed_roles) / 2

    def format_stats(self, short=False) -> str:
        return (
            f'`☠️` {format_plural(self.total_punishments, ("наказание", "наказания", "наказаний"))}\n'
            f'`🎭` {format_plural(self.total_roles, ("роль", "роли", "ролей"))}\n'
            f'`⏱️` **{templates.time(self.online_time, display_hour=True)}**'
        ) if not short else (
            f'`☠️` {self.total_punishments}, '
            f'`🎭` {self.total_roles:g}, '
            f'`⏱️` {templates.time(self.online_time, display_hour=True)}'
        )

@dataclass
class MonthModeratorStats:
    dates: Dict[str, ModeratorStats]

    @property
    def total_punishments(self) -> int:
        return sum(stats.total_punishments for stats in self.dates.values())

    @property
    def total_roles(self) -> float:
        return sum(stats.total_roles for stats in self.dates.values())

    @property
    def total_online_time(self) -> int:
        return sum(stats.online_time for stats in self.dates.values())

    def format_stats(self) -> str:
        start_date = datetime.datetime.strptime(list(self.dates.keys())[0], '%Y-%m-%d').replace(day=1)
        end_date = min((start_date + datetime.timedelta(days=31)).replace(day=1), datetime.datetime.now())
        null_days = 0

        text = ''
        for day in date_range(start_date, end_date):
            if day not in self.dates:
                null_days += 1
            else:
                if null_days:
                    text += f'-# \- {format_plural(null_days, ("день", "дня", "дней"))} без активности\n'
                    null_days = 0

                stats = self.dates[day]
                text += f'**``{".".join(list(reversed(day[2:].split("-"))))}``**: {stats.format_stats(short=True)}\n'
        if null_days:
            text += f'-# \- {format_plural(null_days, ("день", "дня", "дней"))} без активности\n'
        return text

    def format_global_stats(self) -> str:
        return (
            f'`☠️` {format_plural(self.total_punishments, ("наказание", "наказания", "наказаний"))}\n'
            f'`🎭` {format_plural(self.total_roles, ("роль", "роли", "ролей"))}\n'
            f'`⏱️` **{templates.time(self.total_online_time, display_hour=True)}**'
        )