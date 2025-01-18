import datetime
import logging
import re
import traceback
from typing import Tuple

import discord
from discord import app_commands

import security

_action_types = {
    'ban': 'Бан',
    'kick': 'Кик',
    'mute': 'Мут',
    'warn': 'Варн',
    'hide': 'Хайд',
    'role': "роли"
}

_action_notes = {
    'give': "Выдача: ",
    'remove': "Снятие: ",
    'full': "Полный",
    'voice': "Голосовой",
    'text': "Текстовый",
    'global': "Глобальный",
    'temp': "Временный",
    'approve': "Одобрение",
    'reject': "Отклонение",
}


def action(action_type: str, *, short: bool = False) -> str:
    if short:
        action_type = action_type.replace('give', '').replace('remove', '')
    result = [name for template_note_type, name in _action_notes.items() if template_note_type in action_type]
    result += [name for template_action_type, name in _action_types.items() if template_action_type in action_type]
    return ' '.join(result).capitalize()


def user(obj: discord.Member | discord.User | int, dm: bool = False) -> str:
    if isinstance(obj, int):
        return f'<@{obj}>'
    
    result = obj.mention
    if tag := security.user_tag(obj):
        result += f' [{tag}]'
        if dm:
            result += ' ' + obj.display_name.split(']', maxsplit=1)[-1].strip()
    return result


def time(seconds: float | None, precise: bool = False, display_hour: bool = False) -> str:
    if seconds is None:
        return 'Навсегда'

    if seconds < 60:
        return f'{seconds:.0f} сек.'
    elif seconds < 3600:
        minutes = seconds // 60
        local_seconds = seconds % 60
        return f'{minutes:.0f} мин.' if not precise else f'{minutes:.0f} мин. {local_seconds:.0f} сек.'
    elif seconds < 86400 or display_hour:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        local_seconds = seconds % 60
        if precise:
            return f"{hours:.0f} ч. {minutes:.0f} мин. {local_seconds:.0f} сек."
        else:
            return f"{hours:.0f} ч." + (f' {minutes:.0f} мин.' if minutes else '')
    else:
        return f"{seconds // 86400:.0f} дн."


def date(obj: datetime.datetime, *, date_format: str = 'f') -> str:
    return f'<t:{int(obj.astimezone(datetime.UTC).timestamp())}:{date_format}>'


def link(obj: str, alias: str = 'Ссылка') -> str:
    return f'[{alias}]({obj})'


_mention_regex = re.compile(r'<@!?(\d+)>')


def embed_mentions(embed: discord.Embed) -> str:
    all_text = ''
    
    if embed.description:
        all_text += embed.description
        
    if embed.fields:
        for field in embed.fields:
            if not field.value:
                continue
            all_text += field.value
    groups = _mention_regex.findall(all_text)
    groups = list(set(groups))
    return '-# ||' + ', '.join([f'<@{m}>' for m in groups]) + '||' if groups else ''


async def link_action(interaction: discord.Interaction, act, screenshot: list[discord.Message] | None = None, target_message: discord.Message | None = None, db = None, force_proof: bool = False, *, notify_user: bool = True, **objects) -> None:
    if screenshot:
        await interaction.response.send_message('### 📸 Скриншот сообщений\nОжидайте...', ephemeral=True)
    message = await act.log(interaction.guild, screenshot, target_message, db, force_proof=force_proof, **objects)

    if screenshot:
        await interaction.edit_original_response(content=f'## 🥳 Успех!\n[Действие]({message.jump_url}) успешно выполнено.', view=None)
    elif not interaction.response.is_done():
        await interaction.response.send_message(
            f'## 🥳 Успех!\n[Действие]({message.jump_url}) успешно выполнено.',
            ephemeral=True
        )

    if notify_user:
        await act.notify_user(**objects)


async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError | str):
    traceback_info = traceback.format_exc()
    try:
        if interaction.response.is_done():
            print('Unhandled error:', traceback_info)
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Команда ещё недоступна! Попробуйте ещё раз через **{error.retry_after:.2f}** сек!",
                ephemeral=True
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("У вас нет прав", ephemeral=True)
        elif isinstance(error, app_commands.CommandInvokeError) or isinstance(error, str):
            embed = discord.Embed(
                title='💀 Произошла ошибка',
                description=str(error.original if isinstance(error, app_commands.CommandInvokeError) else error),
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            logging.warning(f'Error: {error}')
            await interaction.response.send_message("Произошла ошибка", ephemeral=True)
    except:
        print('Unhandled error:', traceback_info)

def user_notify_description(act, **objects):
    description = f'### Доброго времени суток, {objects['user'].mention}.\n'
    if act.type != 'role_approve':
        if 'role' not in act.type:
            description += f'Вы получили наказание от модератора {objects["moderator"].mention}.\n'
        else:
            if 'remove' in act.type:
                description += 'Вам была снята роль.\n'
            else:
                description += 'Ваше заявление на роль было отклонено.\n'
        description += "-# В случае, если вы не согласны с действиями модератора, вы можете подать жалобу на [форум проекта](https://forum.radmir.games)."
    return description

def role_requested(nickname, role, rang):
    embed = discord.Embed(title='Заявление на роль отправлено', color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    embed.add_field(name='Никнейм', value=nickname, inline=True)
    embed.add_field(name='Должность', value=rang, inline=True)
    embed.add_field(name='Организация', value=role, inline=False)
    embed.set_footer(text='Время отправки заявления')
    return embed

def role_requests(command_id, remove_command_id):
    return f'''# Подача заявления на роль
### Получение роли
Чтобы получить фракционную роль вы должны её запросить используя команду указанную ниже.
### Требования к запросу
1. Вы должны находится в той фракции, роль которой запрашиваете.
2. Вы должны находится на той должности которую указываете.
3. Скриншот статистики должен быть с /c 60.
4. На скриншоте должно быть видно ваш ник, фракцию, должность, номер сервера и время.
5. Скриншоту должно быть не более 24 часов.
6. При скриншотах с Hassle, ID на скриншотах должен совпадать.
-# В случае если вы играете с Hassle, вы можете сделать два скриншота, 1 с /c 60 и второй - статистики. (прикрепить как дополнение) 

# **</role:{command_id}>** - подать заявление
Нажмите на надпись </role:{command_id}>, либо введите ее вручную в чате чтобы подать на роль.
-# Также вы можете снять свою роль командой **</role-remove:{remove_command_id}>**.'''

def role(role):
    return f'<&{role}>'


def format_plural(n: int | float, forms: Tuple[str, str, str]) -> str:
    if n % 10 == 1 and n % 100 != 11:
        form = forms[0]
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        form = forms[1]
    else:
        form = forms[2]
    return f'**{n:g}** {form}'
