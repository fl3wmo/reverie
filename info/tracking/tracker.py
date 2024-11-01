from datetime import datetime
from typing import Optional

import discord

from database import db
from info.tracking.stats import ModeratorStats


class ModeratorTracker:
    def __init__(self, guild: discord.Guild):
        self.guild = guild

    async def get_stats(
            self,
            moderator_id: int,
            start_date: datetime,
            end_date: Optional[datetime] = None
    ) -> ModeratorStats:
        end_date = end_date or start_date

        punishments = await db.actions.by_moderator(
            moderator_id,
            counting=True,
            guild=self.guild.id,
            date_from=start_date,
            date_to=end_date if end_date != start_date else None
        )

        roles_give, roles_remove = await db.roles.moderator_work(
            moderator=moderator_id,
            guild=self.guild.id,
            date_from=start_date,
            date_to=end_date if end_date != start_date else None
        )

        if end_date == start_date:
            online = await db.online.get_info(
                is_open=True,
                user_id=moderator_id,
                guild_id=self.guild.id,
                date=start_date.strftime('%Y-%m-%d')
            )
            online_time = online.total_seconds
        else:
            online_info = await db.online.get_diapason_info(
                moderator_id,
                self.guild.id,
                start_date,
                end_date if end_date != start_date else None,
                True
            )
            online_time = sum(info.total_seconds for info in online_info.values())

        punishments_dict = {}
        for action in punishments:
            punishments_dict.setdefault(action.type, []).append(action)

        roles_dict = {}
        for role in roles_give:
            key = 'Одобрено' if role.approved else 'Отклонено'
            roles_dict.setdefault(key, []).append(role)
        if roles_remove:
            roles_dict['Снято'] = roles_remove

        return ModeratorStats(
            punishments=punishments_dict,
            roles=roles_dict,
            online_time=online_time,
            removed_roles=roles_remove
        )
