from typing import Dict, List

from core import templates
from database.roles.request import RoleRequest


class StatsFormatter:
    @staticmethod
    def format_actions(actions: Dict[str, List[any]]) -> str:
        if not actions:
            return 'Нет наказаний'

        sorted_actions = sorted(actions.items(), key=lambda x: len(x[1]), reverse=True)
        return '\n・ '.join(
            f'{templates.action(action_type, short=True)}: `{len(acts)}`'
            for action_type, acts in sorted_actions
        )

    @staticmethod
    def format_roles(roles: Dict[str, List[RoleRequest]]) -> str:
        if not roles:
            return 'Нет действий'

        sorted_roles = sorted(roles.items(), key=lambda x: len(x[1]), reverse=True)
        return '\n・ '.join(
            f'{role}: `{len(acts)}`'
            for role, acts in sorted_roles
        )
