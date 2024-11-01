import re
from typing import Any

import discord
from discord import Interaction
from discord._types import ClientT

import security
import templates
from database import db
from database.roles.request import RequestStatus, RoleRequest


class UnderReviewIndicator(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                disabled=True,
                label='На рассмотрении',
                emoji='⏳'
            )
        )


class RoleRequestHandler:
    def __init__(self, action_id: int) -> None:
        self.action_id = action_id

    async def update_status_message(self, interaction: discord.Interaction, request: RoleRequest) -> None:
        channel = [c for c in interaction.guild.channels if 'запрос-роли' in c.name][0]
        status_message = await channel.fetch_message(request.status_message)
        status = 'одобрено' if request.status == RequestStatus.APPROVED else 'отклонено'
        color = discord.Color.green() if request.status == RequestStatus.APPROVED else discord.Color.red()
        embed = status_message.embeds[0]
        embed.colour = color
        embed.title = ' '.join(embed.title.split()[:-1] + [status])
        await status_message.edit(embed=embed, view=None)

        _, user = await interaction.client.getch_any(interaction.guild, request.user)
        await request.notify_user(user, interaction.user)

    async def edit_interaction_message(self, interaction: discord.Interaction, request, specified_view: discord.ui.View = None) -> None:
        embed = request.to_embed()
        if not interaction.response.is_done():
            await interaction.response.edit_message(content=templates.embed_mentions(embed), embed=embed, view=specified_view or request.to_view())
        else:
            await interaction.message.edit(content=templates.embed_mentions(embed), embed=embed, view=specified_view or request.to_view())

        if request.status in (RequestStatus.APPROVED, RequestStatus.REJECTED):
            log_channel = [c for c in interaction.guild.channels if 'логи-ролей' in c.name][0]
            await log_channel.send(embed=embed)

class TakeRole(discord.ui.DynamicItem[discord.ui.Button], template='roles:take:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label='Взять роль',
                style=discord.ButtonStyle.grey,
                custom_id=f'roles:take:{action_id}',
                emoji='🔥',
            )
        )
        self.action_id: int = action_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    @security.restricted(security.PermissionLevel.MD)
    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        request = await db.roles.get_request_by_id(self.action_id)
        if not request or request.moderator:
            raise ValueError('Заявление уже взято')

        await db.roles.take_request(self.action_id, interaction.user.id)
        request.moderator = interaction.user.id

        embed = request.to_embed()
        await interaction.response.edit_message(content=templates.embed_mentions(embed), embed=embed, view=request.to_view())

class ApproveRole(discord.ui.DynamicItem[discord.ui.Button], template='roles:approve:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label='Одобрить',
                style=discord.ButtonStyle.success,
                custom_id=f'roles:approve:{action_id}',
                emoji='\N{THUMBS UP SIGN}',
            )
        )
        self.handler = RoleRequestHandler(action_id)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    @security.restricted(security.PermissionLevel.MD)
    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        await db.roles.check_request(interaction.user.id, self.handler.action_id, True)
        request = await db.roles.get_request_by_id(self.handler.action_id)
        await self.handler.edit_interaction_message(interaction, request)
        await self.handler.update_status_message(interaction, request)

        member, user = await interaction.client.getch_any(interaction.guild, request.user)
        if member:
            await request.role_info.give(member, request.nickname, request.rang)

class RejectRole(discord.ui.DynamicItem[discord.ui.Select], template='roles:reject:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Select(
                max_values=len(db.roles.reasons_dict),
                placeholder='Выберите причину',
                options=[discord.SelectOption(label=k, emoji=v[0], description=v[1]) for k, v in db.roles.reasons_dict.items()],
                custom_id=f'roles:reject:{action_id}',
            )
        )
        self.handler = RoleRequestHandler(action_id)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Select, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    @security.restricted(security.PermissionLevel.MD)
    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        selected_options = interaction.data['values']
        reasons = [f'**{v[0]} {k}**\n{v[1]}' for k, v in db.roles.reasons_dict.items() if k in selected_options]
        reason = '\n\n'.join(reasons)
        await db.roles.check_request(interaction.user.id, self.handler.action_id, False, reason)
        request = await db.roles.get_request_by_id(self.handler.action_id)
        await self.handler.edit_interaction_message(interaction, request)
        await self.handler.update_status_message(interaction, request)

class ReviewApproveRole(discord.ui.DynamicItem[discord.ui.Button], template='roles:review_approve:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label='Верно',
                style=discord.ButtonStyle.success,
                custom_id=f'roles:review_approve:{action_id}',
                emoji='\N{THUMBS UP SIGN}',
            )
        )
        self.handler = RoleRequestHandler(action_id)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    @security.restricted(security.PermissionLevel.GMD)
    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        await db.roles.review_request(interaction.user.id, self.handler.action_id, True)
        request = await db.roles.get_request_by_id(self.handler.action_id)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=interaction.user.display_name, emoji='\N{THUMBS UP SIGN}',
                                        style=discord.ButtonStyle.grey, disabled=True))

        await self.handler.edit_interaction_message(interaction, request, view)

class ReasonChange(discord.ui.Modal):
    reason = discord.ui.TextInput(label='Причина')

    def __init__(self, reason, callback):
        self.default_reason = reason
        self.reason.default = reason
        self.callback = callback
        super().__init__(title='Изменение причины отказа')

    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        await interaction.response.defer()
        await self.callback(interaction, self.reason.value)

class ReviewPartialApproveRole(discord.ui.DynamicItem[discord.ui.Button], template='roles:review_partial_approve:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label='Частично верно',
                style=discord.ButtonStyle.blurple,
                custom_id=f'roles:review_partial_approve:{action_id}',
                emoji='🤷‍♂️',
            )
        )
        self.handler = RoleRequestHandler(action_id)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    @security.restricted(security.PermissionLevel.GMD)
    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        async def change_reason(modal_interaction: Interaction[ClientT], reason: str):
            await db.roles.review_request(interaction.user.id, self.handler.action_id, True, reason=reason, partial=True)
            request = await db.roles.get_request_by_id(self.handler.action_id)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=interaction.user.display_name, emoji='🤷‍♂️', style=discord.ButtonStyle.blurple, disabled=True))

            await self.handler.edit_interaction_message(interaction, request, view)
        await interaction.response.send_modal(ReasonChange('', change_reason))

class ReviewRejectRole(discord.ui.DynamicItem[discord.ui.Button], template='roles:review_reject:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label='Неверно',
                style=discord.ButtonStyle.danger,
                custom_id=f'roles:review_reject:{action_id}',
                emoji='\N{THUMBS DOWN SIGN}',
            )
        )
        self.handler = RoleRequestHandler(action_id)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    @security.restricted(security.PermissionLevel.GMD)
    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        async def change_reason(modal_interaction: Interaction[ClientT], reason: str):
            await db.roles.review_request(interaction.user.id, self.handler.action_id, False, reason=reason)
            request = await db.roles.get_request_by_id(self.handler.action_id)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=interaction.user.display_name, emoji='\N{THUMBS DOWN SIGN}', style=discord.ButtonStyle.danger, disabled=True))

            await self.handler.edit_interaction_message(interaction, request, view)
            await self.handler.update_status_message(interaction, request)

            if not await db.roles.is_request_last(request.id, request.user, request.guild):
                return

            member, user = await interaction.client.getch_any(interaction.guild, request.user)
            if member:
                if request.status == RequestStatus.REJECTED:
                    await request.role_info.remove(member)
                else:
                    await request.role_info.give(member, request.nickname, request.rang)
        await interaction.response.send_modal(ReasonChange('', change_reason))


def roles_take(action_id: int) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(TakeRole(action_id))
    return view


def roles_check(action_id: int) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(RejectRole(action_id))
    view.add_item(ApproveRole(action_id))
    return view

def roles_review(action_id: int) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(ReviewRejectRole(action_id))
    view.add_item(ReviewApproveRole(action_id))
    view.add_item(ReviewPartialApproveRole(action_id))
    return view
