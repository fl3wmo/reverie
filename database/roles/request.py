import datetime
import enum
from dataclasses import dataclass, asdict

import discord

import buttons
import templates
from database.actions.action import Act
from features import seconds_to_time
from info.roles import RoleInfo, role_info


class RequestStatus(enum.IntEnum):
    NEW = 0
    APPROVED = 1
    REJECTED = 2
    UNDER_REVIEW = 3


@dataclass
class RoleRequest:
    id: int
    user: int
    guild: int
    nickname: str
    role: str
    rang: int
    approved: bool
    counting: bool
    sent_at: datetime.datetime
    status_message: int
    moderator: int = None
    taken_at: datetime.datetime = None
    checked_at: datetime.datetime = None
    reason: str = None
    reviewer: int = None
    _id: str = None

    @property
    def status(self) -> RequestStatus:
        if self.approved:
            return RequestStatus.APPROVED
        if self.checked_at:
            return RequestStatus.REJECTED
        if self.moderator:
            return RequestStatus.UNDER_REVIEW
        return RequestStatus.NEW

    @property
    def role_info(self) -> RoleInfo:
        return role_info.get(self.role)

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop('_id')
        return data

    def to_embed(self, for_moderator: bool = True, guild: discord.Guild = None) -> discord.Embed:
        title_prefix = '📗 Одобренное' if self.status == RequestStatus.APPROVED else '📕 Отклоненное' if self.status == RequestStatus.REJECTED else '📙 Новое'
        title_postfix = ' (рассматривается)' if self.status == RequestStatus.UNDER_REVIEW else ' (пересмотрено)' if self.reviewer and not for_moderator else ''
        embed = discord.Embed(
            title=f'{title_prefix} заявление на роль {title_postfix}',
            color=discord.Color.green() if self.status == RequestStatus.APPROVED else discord.Color.red() if self.status == RequestStatus.REJECTED else discord.Color.orange(),
            timestamp=self.sent_at.replace(tzinfo=datetime.timezone.utc)
        )

        if not for_moderator:
            embed.set_author(name=f'Отправлено из: {guild.name}', icon_url=guild.icon.url)

        embed.add_field(name='Никнейм', value=self.nickname)
        embed.add_field(name='Роль', value=self.role)
        embed.add_field(name='Ранг', value=f'[{self.rang}] {self.role_info.rang_name(self.rang)}')
        embed.add_field(name='Пользователь', value=templates.user(self.user))

        if self.moderator:
            embed.add_field(
                name='Модератор',
                value=templates.user(self.moderator) +
                      (f' (проверил за {seconds_to_time(round((self.checked_at - self.taken_at).total_seconds()))})' if self.checked_at else '')
            )
        if self.reviewer:
            embed.add_field(name='Следящий', value=templates.user(self.reviewer))
        if self.reason and (self.status == RequestStatus.REJECTED or for_moderator):
            embed.add_field(name='Причина отказа', value=self.reason, inline=False)
        embed.set_footer(text=f'Заявление на роль №{self.id}')

        return embed

    async def notify_user(self, user: discord.User, moderator: discord.Member = None):
        act = Act(id=self.id, at=datetime.datetime.now(datetime.UTC), user=self.user, guild=self.guild, moderator=self.moderator, type='role_approve' if self.status == RequestStatus.APPROVED else 'role_reject', reviewer=self.reviewer, reason=self.reason, counting=False)
        await act.notify_user(self.to_embed(for_moderator=False, guild=moderator.guild), user=user, moderator=moderator)

    def to_view(self) -> discord.ui.View:
        return buttons.roles_check(self.id) if self.status == RequestStatus.UNDER_REVIEW \
            else buttons.roles_take(self.id) if self.status == RequestStatus.NEW \
            else buttons.roles_review(self.id) if self.reviewer is None else None
