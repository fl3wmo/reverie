import asyncio
from typing import NamedTuple

import discord
from discord.ext import commands
from discord import app_commands

import security
import templates
import validation
from bot import EsBot
from buttons.roles import UnderReviewIndicator
from database import db
from features import Pagination, find_channel_by_name
from info.roles import role_info, RoleInfo


def get_organization_roles(member: discord.Member) -> list[RoleInfo]:
    """Получение ролей организации у пользователя."""
    return [role for role in role_info.values() if role.find(member.roles)]

class ActionInfo(NamedTuple):
    action_text: str

    def to_text(self, index: int) -> str:
        return f'### {index}. {self.action_text}'

class RolesCog(commands.Cog):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.roles
        self.ctx_menu = app_commands.ContextMenu(
            name='снять роль фракции', callback=self.remove_role_context
        )
        self.ctx_menu.default_permissions = discord.Permissions(manage_nicknames=True)
        self.bot.tree.add_command(self.ctx_menu)

    async def rang_callback(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[int]]:
        current = 0 if not current.isdecimal() else int(current)
        user_choice = interaction.namespace['организация']
        role = role_info.get(user_choice)

        if not role:
            return []

        ranks = [(current, role.rangs[current - 1])] if current and len(role.rangs) >= current >= 1 else enumerate(role.rangs, 1)
        return [app_commands.Choice(name=f'[{v}] {k}', value=v) for v, k in ranks]

    def requests_channel(self, guild: discord.Guild) -> discord.TextChannel:
        return find_channel_by_name(guild, 'запрос-роли')

    def moderator_channel(self, guild: discord.Guild) -> discord.TextChannel:
        return find_channel_by_name(guild, 'заявки-на-роли')

    async def validate_role_request(self, interaction: discord.Interaction, nickname: str, organization: str, rang: int,
                                    photo_proof: discord.Attachment) -> tuple[str, RoleInfo]:
        """Проверка валидности заявки на роль."""
        channel = self.requests_channel(interaction.guild)
        if channel.id != interaction.channel.id:
            raise ValueError(f'Команда доступна только в канале {channel.mention}')

        if await self.db.get_request(interaction.user.id, interaction.guild.id):
            raise ValueError('У вас уже есть заявление на роль. Ожидайте его рассмотрения.')

        if not (photo_proof.content_type or "").startswith('image/') or photo_proof.size > 8_000_000:
            raise ValueError('Файл должен быть изображением и не превышать 8MB.')

        nickname = nickname.replace('_', ' ').strip()
        validation.nickname(nickname)

        requested_role = role_info[organization]
        if rang > len(requested_role.rangs):
            raise ValueError('Ранг превышает количество доступных рангов в организации')

        return nickname, requested_role

    async def handle_existing_role(self, interaction: discord.Interaction, requested_role, rang: int, nickname: str) -> None:
        """Обработка ситуации, когда у пользователя уже есть роль."""
        await interaction.response.send_message('## Успех ✅\nВаш никнейм изменён на соответствующий вашей должности.', ephemeral=True)
        await interaction.user.edit(nick=requested_role.form_nickname(rang, nickname))

    async def handle_new_role_request(self, interaction: discord.Interaction, nickname: str, organization: str, rang: int,
                                      requested_role, photo_proof: discord.Attachment, photo_additional: discord.Attachment = None) -> None:
        """Обработка новой заявки на роль."""
        embed = templates.role_requested(nickname, organization, f'[{rang}] {requested_role.rang_name(rang)}')
        await interaction.response.send_message(embed=embed, view=UnderReviewIndicator())

        await self.update_message(interaction.channel, self.bot.command_ids.get('role', 0))

        roles = get_organization_roles(interaction.user)
        for role in roles:
            await role.remove(interaction.user)

        request = await self.db.add_request(
            user=interaction.user.id,
            guild=interaction.guild.id,
            nickname=nickname,
            role=organization,
            rang=rang,
            status_message=(await interaction.original_response()).id
        )
        embed = request.to_embed()
        files = [await photo_proof.to_file()]
        if photo_additional:
            files.append(await photo_additional.to_file())
        message = await self.moderator_channel(interaction.guild).send(content=templates.embed_mentions(embed), embed=embed, view=request.to_view(), files=files)

        async def reminder(moderators_message, request_id):
            old_request = await self.db.get_request_by_id(request_id)
            if old_request.moderator:
                return
            guild = moderators_message.guild
            await self.moderator_channel(guild).send(
                f'## Напоминание {security.role_checker(guild).mention}\nЗаявка на роль не рассмотрена в течение 5 минут.\n'
                f'Пожалуйста, проверьте её.'
            )

        await asyncio.sleep(300)
        await reminder(message, request.id)

    async def update_message(self, channel: discord.TextChannel, command_id: int) -> discord.Message:
        """Обновление сообщения в канале заявок на роли."""
        async for message in channel.history(limit=5):
            if message.author.id == self.bot.user.id and not message.embeds:
                await message.delete()
                return await message.channel.send(templates.role_requests(command_id))

    @app_commands.command(name='role', description='Подать заявление на роль')
    @app_commands.rename(nickname='никнейм', organization='организация', rang='ранг', photo_proof='скриншот-статистики',
                         photo_additional='дополнение-статистики')
    @app_commands.describe(
        nickname='Ваш никнейм',
        organization='Организация, в которой вы состоите',
        rang='Ваш ранг в организации',
        photo_proof='Скриншот статистики',
        photo_additional='Дополнительный скриншот для игроков Hassle'
    )
    @app_commands.choices(organization=[app_commands.Choice(name=role, value=role) for role in role_info.keys()])
    @app_commands.autocomplete(rang=rang_callback)
    async def request_role(self, interaction: discord.Interaction, nickname: app_commands.Range[str, 3, 19],
                           organization: app_commands.Choice[str], rang: app_commands.Range[int, 1, 8],
                           photo_proof: discord.Attachment, photo_additional: discord.Attachment = None):
        """Основная команда для подачи заявления на роль."""
        nickname, requested_role = await self.validate_role_request(interaction, nickname, organization.value, rang, photo_proof)

        if requested_role.find(interaction.user.roles):
            await self.handle_existing_role(interaction, requested_role, rang, nickname)
        else:
            await self.handle_new_role_request(interaction, nickname, organization.value, rang, requested_role, photo_proof, photo_additional)

    @app_commands.command(name='role-remove', description='Снять роль фракции')
    async def remove_role(self, interaction: discord.Interaction):
        """Команда для снятия роли."""
        if not (roles := get_organization_roles(interaction.user)):
            return await interaction.response.send_message('У вас нет роли', ephemeral=True)

        for role in roles:
            await role.remove(interaction.user)

        await interaction.response.send_message('Роль успешно снята', ephemeral=True)

    @app_commands.command(name='role-history', description='История ролей пользователя')
    @app_commands.rename(user='пользователь')
    @app_commands.describe(user='Пользователь, историю ролей которого нужно посмотреть')
    async def role_history(self, interaction: discord.Interaction, user: str):
        """Команда для просмотра истории ролей пользователя."""
        member, user = await self.bot.getch_any(interaction.guild, user, interaction.user)
        roles = await self.db.role_history(interaction.guild.id, user.id)
        if not roles:
            raise ValueError('У пользователя нет истории ролей')

        paginator = Pagination(
            bot=self.bot,
            interaction=interaction,
            owner=interaction.user,
            data=list([(index, ActionInfo(action_text=str(role))) for index, role in enumerate(roles, 1)]),
            page_size=5,
            embed_title="История ролей",
        )
        
        await paginator.send_initial_message()

    @app_commands.command(name='role-info', description='Информация о роли')
    @app_commands.rename(request_id='id')
    @app_commands.describe(request_id='ID заявки')
    @app_commands.default_permissions(manage_nicknames=True)
    @security.restricted(security.PermissionLevel.MD)
    async def role_info(self, interaction: discord.Interaction, request_id: int):
        """Команда для просмотра информации о роли."""
        request = await self.db.get_request_by_id(request_id)
        if not request:
            raise ValueError('Заявка не найдена')

        embed = request.to_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def remove_role_context(self, interaction: discord.Interaction, target: discord.Member):
        """Контекстное меню для снятия роли."""
        if security.user_level(interaction.user) < security.PermissionLevel.MD:
            raise ValueError('У вас нет прав')
        security.user_permissions_compare(interaction.user, target)

        if not (roles := get_organization_roles(target)):
            return await interaction.response.send_message('У пользователя нет роли', ephemeral=True)

        role_names = [list(role_info.keys())[list(role_info.values()).index(role)] for role in roles]
        for role in roles:
            await role.remove(target)
        await interaction.response.send_message('Роль успешно снята', ephemeral=True)

        remove = await self.db.remove_roles(target.id, interaction.guild.id, role_names, interaction.user.id)
        logs_channel = find_channel_by_name(interaction.guild, 'логи-ролей')

        embed = remove.to_embed()
        await logs_channel.send(templates.embed_mentions(embed), embed=embed)
        await remove.notify_user(target, interaction.user)


async def setup(bot: EsBot):
    await bot.add_cog(RolesCog(bot))
