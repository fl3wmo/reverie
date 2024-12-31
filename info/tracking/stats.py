import datetime
from dataclasses import dataclass
from typing import Dict, List

import templates
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
        sorted_dates = sorted(self.dates.keys(), key=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
        result = []

        start_date = datetime.datetime.strptime(f"{datetime.datetime.now().year}-{datetime.datetime.now().month:02d}-01", '%Y-%m-%d')
        end_date = datetime.datetime.strptime(f"{datetime.datetime.now().year}-{datetime.datetime.now().month + 1:02d}-01", '%Y-%m-%d') - datetime.timedelta(days=1)

        first_logged_date = datetime.datetime.strptime(sorted_dates[0], '%Y-%m-%d') if sorted_dates else None
        if first_logged_date and (first_logged_date > start_date):
            gap = (first_logged_date - start_date).days
            for j in range(gap):
                missing_date = (start_date + datetime.timedelta(days=j)).strftime('%Y-%m-%d')
                formatted_date = ".".join(reversed(missing_date[2:].split("-")))
                result.append(f"**``{formatted_date}``**: -#{j + 1} нет активности")

        for i in range(len(sorted_dates)):
            current_date = datetime.datetime.strptime(sorted_dates[i], '%Y-%m-%d')

            if i > 0:
                previous_date = datetime.datetime.strptime(sorted_dates[i - 1], '%Y-%m-%d')
                gap = (current_date - previous_date).days - 1

                if gap > 0:
                    for j in range(1, gap + 1):
                        missing_date = (previous_date + datetime.timedelta(days=j)).strftime('%Y-%m-%d')
                        formatted_date = ".".join(reversed(missing_date[2:].split("-")))
                        result.append(f"**``{formatted_date}``**: -#{j} нет активности")

            formatted_date = ".".join(reversed(sorted_dates[i][2:].split("-")))
            result.append(f'**``{formatted_date}``**: {self.dates[sorted_dates[i]].format_stats(short=True)}')

        last_logged_date = datetime.datetime.strptime(sorted_dates[-1], '%Y-%m-%d') if sorted_dates else None
        if last_logged_date and (last_logged_date < end_date):
            gap = (end_date - last_logged_date).days
            for j in range(gap):
                missing_date = (last_logged_date + datetime.timedelta(days=j + 1)).strftime('%Y-%m-%d')
                formatted_date = ".".join(reversed(missing_date[2:].split("-")))
                result.append(f"**``{formatted_date}``**: -#{j + 1} нет активности")

        return '\n'.join(result)

    def format_global_stats(self) -> str:
        return (
            f'`☠️` {format_plural(self.total_punishments, ("наказание", "наказания", "наказаний"))}\n'
            f'`🎭` {format_plural(self.total_roles, ("роль", "роли", "ролей"))}\n'
            f'`⏱️` **{templates.time(self.total_online_time, display_hour=True)}**'
        )