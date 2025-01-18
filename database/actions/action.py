import datetime
from dataclasses import dataclass, asdict
from typing import Literal

import discord

import buttons
import features
import security
import templates

type action = Literal[
    'role_approve', 'role_reject', 'role_remove',
    'warn_give', 'warn_remove',
    'hide_give', 'hide_remove',
    'ban_local_give', 'ban_local_remove',
    'ban_global_give', 'ban_global_remove',
    'mute_text_give', 'mute_text_remove',
    'mute_voice_give', 'mute_voice_remove',
    'mute_full_give', 'mute_full_remove',
    'temp_mute_give', 'temp_mute_remove',
]

def _action_category(action_type: action, fast: bool = False) -> str:
    return 'roles' if 'role' in action_type else 'punishments' if not fast else 'punishments_fast'


_log_channels = {
    'roles': "логи-ролей",
    'punishments': "выдача-наказаний",
    'punishments_fast': 'запрос-на-выдачу'
}

def gmd_indicator() -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(label='Выдано от GMD+', emoji='\N{THUMBS UP SIGN}', style=discord.ButtonStyle.secondary,
                          disabled=True))
    return view

@dataclass
class Act:
    id: int
    at: datetime.datetime
    user: int
    guild: int
    moderator: int
    type: action
    counting: bool
    _id: str = None
    reviewer: int = None
    duration: float = None
    reason: str = None
    prove_link: str = None

    @property
    def as_dict(self):
        data = asdict(self)
        data.pop('_id')
        return data

    def _log_channel(self, guild: discord.Guild, fast: bool = False) -> discord.TextChannel:
        search = _log_channels[_action_category(self.type, fast=fast)]
        for channel in guild.text_channels:
            if search in channel.name:
                return channel
        raise ValueError(f'Не найден канал логов {search}')

    def to_text(self, local_id: int = None) -> str:
        if not local_id:
            local_id = self.id
        text = f'### {local_id}. {templates.action(self.type, short=True)}\n'
        if self.at:
            text += f'> Дата: {templates.date(self.at, date_format='d')}\n'
        if self.reason:
            text += f'> Причина: {self.reason[:30]}{"..." if len(self.reason) > 30 else ""}\n'
        if self.duration:
            text += f'> Длительность: {templates.time(self.duration)}\n'
        if self.moderator:
            text += f'> -# Акт: {self.id}. Модератор: {templates.user(self.moderator)}'
        return text


    def to_embed(self, under_verify: bool, *, for_moderator: bool = True, **objects) -> discord.Embed:
        embed = discord.Embed(
            title=templates.action(self.type),
            color=discord.Color.gold() if under_verify else discord.Color.random(),
            timestamp=self.at.replace(tzinfo=datetime.UTC)
        )

        if for_moderator:
            embed.add_field(name='Пользователь', value=templates.user(objects.get('user', self.user)))
        else:
            embed.description = templates.user_notify_description(self, **objects)
            embed.set_author(name='Уведомление из: ' + objects['moderator'].guild.name, icon_url=objects['moderator'].guild.icon.url)

        embed.add_field(name='Модератор', value=templates.user(objects.get('moderator', self.moderator), dm=not for_moderator))
        embed.set_footer(text=f'Акт №{self.id}')

        if self.reviewer and self.reviewer != self.moderator:
            embed.add_field(name='Проверяющий', value=templates.user(objects.get('reviewer', self.reviewer), dm=not for_moderator))

        if self.duration:
            embed.add_field(name='Длительность', value=templates.time(self.duration))
        if not for_moderator:
            embed.add_field(
                name='Время окончания',
                value=templates.date(self.at + datetime.timedelta(seconds=self.duration), date_format='R'),
                inline=True
            )
        if self.prove_link and for_moderator:
            embed.add_field(name='Доказательство', value=templates.link(self.prove_link), inline=False)
        if self.reason:
            embed.add_field(name='Причина', value=self.reason, inline=False)
        return embed

    async def log(self, guild: discord.Guild, screenshot: list[discord.Message] | None = None, target_message: discord.Message | None = None, db = None, force_proof: bool = False, **objects) -> discord.Message:
        under_verify = not self.reviewer
        embed = self.to_embed(under_verify=under_verify, **objects)
        mentions = templates.embed_mentions(embed)
        ping_reviewers = under_verify and (('ban' in self.type and 'give' in self.type) or 'warn' in self.type)
        if ping_reviewers:
            mentions += ' ' + ' '.join([role.mention for role in security.reviewers(guild)])
        channel = self._log_channel(guild, fast=ping_reviewers)
        auto_review = self.reviewer == self.moderator and 'warn' not in self.type
        message: discord.Message = await channel.send(mentions, embed=embed, view=buttons.punishment_review(self.id) if not self.reviewer else (None if not auto_review else gmd_indicator()))
        if screenshot:
            await features.screenshot_messages(message, target_message, screenshot, action_id=self.id, db=db)
        elif under_verify or force_proof:
            thread = await message.create_thread(name='Доказательства', auto_archive_duration=60)
            try:
                await thread.add_user(discord.Object(id=self.moderator))
            except:
                pass
        return message

    async def notify_user(self, specified_embed=None, **objects) -> None:
        user = objects.get('user')
        if user.id != self.user:
            raise ValueError('Пользователь не совпадает с указанным в действии')

        embed = self.to_embed(under_verify=False, for_moderator=False, **objects)
        view = buttons.ForumLink() if self.type != 'role_approve' else None
        try:
            await user.send(embed=specified_embed or embed, view=view)
        except discord.Forbidden:
            return
        except discord.HTTPException:
            return
        except Exception as e:
            print(e)

    async def set_prove_link(self, link: str) -> None:
        await self.db.set_prove_link(self.id, link)
