import typing

import discord
from discord import app_commands
from fuzzywuzzy import process
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from database.punishments.bans import Bans
from database.punishments.warns import Warns

if typing.TYPE_CHECKING:
    from database.actions.general import Actions
from database.punishments.mutes import Mutes


class Punishments:
    def __init__(self, client: MotorClient, actions: 'Actions'):
        self._client = client
        self._db = self._client['Punishments']
        self.mutes = Mutes(self._db['mutes'], actions)
        self.bans = Bans(self._db['bans'], actions)
        self.warns = Warns(self._db['warns'], actions)
        
        self.reasons = {
            'Использование команд, не предназначенных для игроков',
            'Распространение закрытой от игроков информации',
            'Отправка файлов, доступных только для скачивания',
            'Деструктивные действия',
            'Реклама стороннего ПО',
            'Оскорбление сотрудников проекта',
            'Трансляция сторонней игры из индустрии GTA',
            'Попытка слива модерации или администрации',
            'Изменение голоса в целях обмана',
            'Оскорбление или упоминание родителей',
            'Оскорбление в реакциях',
            'Реклама',
            'Отправка скримеров',
            'Расизм',
            'Дискуссии на тему веры или религии',
            'Отправка или включение скримера',
            'Помеха модерации',
            'Распространение ложной информации',
            'Невидимый ник',
            'Капс',
            'Флуд',
            'Обман пользователей, модерации или администрации',
            'Спам',
            '18+ контент в статусе/аватаре/обо мне/никнейме',
            'Обход наказания',
            'Нацизм',
            'Игнорирование просьб модерации или администрации',
            'Политика',
            'Покупка/реклама или признание в покупке/продаже вирт',
            'Оскорбление проекта',
            'Оскорбительный или неадекватный статус/аватар/обо мне/никнейм',
            'Трансляция читов',
            'Наличие тега, неподтвеждённого ролью',
            'Транслирование посторонних звуков в микрофон',
            'Дискуссии на тему веры или религииНеадекватное поведение',
            '18+ контент',
            'Распространение личной информации или угроза распространения',
            'Распространение или угроза распространения личной информации',
            'Оскорбление',
            'Упоминание покупки или продажи аккаунтов',
            'Транслирование посторонних звуков в микрофон',
        }

    async def reasons_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        choices = process.extract(current, self.reasons, limit=25)
        return [
            app_commands.Choice(name=reason, value=reason)
            for reason, index in choices
            if index > 50
        ]