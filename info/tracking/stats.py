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

    def format_stats(self) -> str:
        return (
            f'`☠️` {format_plural(self.total_punishments, ("наказание", "наказания", "наказаний"))}\n'
            f'`🎭` {format_plural(self.total_roles, ("роль", "роли", "ролей"))}\n'
            f'`⏱️` **{templates.time(self.online_time)}**'
        )
