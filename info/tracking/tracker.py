from datetime import datetime
from typing import Optional

import discord

from database import db
from info.tracking.stats import ModeratorStats, MonthModeratorStats


class ModeratorTracker:
    def __init__(self, guild: discord.Guild):
        self.guild = guild

    async def get_stats(
            self,
            moderator_id: int,
            start_date: datetime,
            end_date: Optional[datetime] = None,
            return_by_dates: bool = False
    ) -> ModeratorStats | MonthModeratorStats:
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

        online_info = None
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

        if return_by_dates and online_info is not None:
            date_stats = {}
            for date, info in online_info.items():
                date_stats.setdefault(date, {})['online_time'] = info.total_seconds

            for action in punishments:
                date = action.at.strftime('%Y-%m-%d')
                date_stats.setdefault(date, {}).setdefault('punishments', {}).setdefault(action.type, []).append(action)

            for role in roles_give:
                date = role.checked_at.strftime('%Y-%m-%d')
                key = 'Одобрено' if role.approved else 'Отклонено'
                date_stats.setdefault(date, {}).setdefault('roles', {}).setdefault(key, []).append(role)

            for role in roles_remove:
                date = role.at.strftime('%Y-%m-%d')
                date_stats.setdefault(date, {}).setdefault('roles', {}).setdefault('Снято', []).append(role)

            return MonthModeratorStats(
                dates={
                    date: ModeratorStats(
                        punishments=stats.get('punishments', {}),
                        roles={'Одобрено': stats.get('roles', {}).get('Одобрено', []),
                                 'Отклонено': stats.get('roles', {}).get('Отклонено', []),
                                 'Снято': stats.get('roles', {}).get('Снято', [])},
                        online_time=stats.get('online_time', 0),
                        removed_roles=stats.get('roles', {}).get('Снято', [])
                    )
                    for date, stats in date_stats.items()
                }
            )

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
