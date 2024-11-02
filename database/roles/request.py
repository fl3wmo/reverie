import datetime
import enum
from dataclasses import dataclass, asdict

import discord

import buttons
import templates
from database.actions.action import Act
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
    review_reason: str = None
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

    @property
    def status_emoji(self) -> str:
        return '📗' if self.status == RequestStatus.APPROVED else '📕' if self.status == RequestStatus.REJECTED else '📙'

    @property
    def status_symbol(self) -> str:
        return '+' if self.status == RequestStatus.APPROVED else '-' if self.status == RequestStatus.REJECTED else '?'

    @property
    def status_text(self) -> str:
        return 'Одобренное' if self.status == RequestStatus.APPROVED else 'Отклоненное' if self.status == RequestStatus.REJECTED else 'Новое'

    def to_embed(self, for_moderator: bool = True, guild: discord.Guild = None) -> discord.Embed:
        title_postfix = ' (рассматривается)' if self.status == RequestStatus.UNDER_REVIEW else ' (пересмотрено)' if self.reviewer and not for_moderator else ''
        embed = discord.Embed(
            title=f'{self.status_emoji} {self.status_text} заявление на роль {title_postfix}',
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
                value=templates.user(self.moderator)
            )
        if self.reviewer:
            embed.add_field(name='Следящий', value=templates.user(self.reviewer))
        if self.reason and (self.status == RequestStatus.REJECTED or for_moderator):
            embed.add_field(name='Причина отказа', value=self.reason, inline=False)
        if self.review_reason and for_moderator:
            embed.add_field(name='Причина пересмотра', value=self.review_reason, inline=False)
        embed.set_footer(text=f'Заявление на роль №{self.id}' + (f' (проверено за {templates.time(round((self.checked_at - self.taken_at).total_seconds()), precise=True)})' if for_moderator and self.checked_at and self.taken_at else ''))

        return embed

    def __str__(self) -> str:
        parts = [
            f"[{self.status_symbol}] {self.status_text}",
            f'> Дата: {templates.date(self.sent_at, date_format="d")}',
            f"> Никнейм: {self.nickname}",
            f"> Фракция: {self.role}",
            f"> Ранг: [{self.rang}] {self.role_info.rang_name(self.rang)}",
            f"> -# Запрос: {self.id}"
        ]
        
        if self.moderator:
            parts[-1] += f". Модератор: <@{self.moderator}>"
            
        return "\n".join(parts)

    async def notify_user(self, user: discord.User, moderator: discord.Member = None):
        act = Act(id=self.id, at=datetime.datetime.now(datetime.UTC), user=self.user, guild=self.guild, moderator=self.moderator, type='role_approve' if self.status == RequestStatus.APPROVED else 'role_reject', reviewer=self.reviewer, reason=self.reason, counting=False)
        await act.notify_user(self.to_embed(for_moderator=False, guild=moderator.guild), user=user, moderator=moderator)

    def to_view(self) -> discord.ui.View:
        return buttons.roles_check(self.id) if self.status == RequestStatus.UNDER_REVIEW \
            else buttons.roles_take(self.id) if self.status == RequestStatus.NEW \
            else buttons.roles_review(self.id) if self.reviewer is None else None
