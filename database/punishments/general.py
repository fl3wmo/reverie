import typing
from typing import Optional

import discord
from discord import app_commands
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from database.punishments.bans import Bans
from database.punishments.hides import Hides
from database.punishments.warns import Warns
from info.punishments import reason_hints, profile_reasons, tags

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
        self.hides = Hides(self._db['hides'], actions)


    def _get_filtered_categories(self, exclude: Optional[list[str]] = None, include: Optional[list[str]] = None) -> \
            list[str]:
        if not (exclude is None) ^ (include is None):
            raise ValueError("Either exclude or include must be specified, not both")
        return [c for c in reason_hints if c in include] if include else [c for c in reason_hints if c not in exclude]

    def _generate_choices(self, categories: list[str]) -> list[app_commands.Choice]:
        choices = []
        for category in categories:
            for key, value in reason_hints.get(category, {}).items():
                choices.append(app_commands.Choice(name=f"{category}: {key}", value=value))
        return choices

    @staticmethod
    def _get_picked_categories(current: str, categories: list[str]) -> list[str]:
        return [cat for cat in categories if cat.startswith(current)]

    @staticmethod
    def _get_tag_extensions(current: str, variant: app_commands.Choice) -> list[str]:
        if not current:
            return []

        extensions = []
        last_char = current[-1]

        if last_char in '([':
            end = ')' if last_char == '(' else ']'
            extensions.extend(f"{tag}{end}" for tag in tags)
        elif current == variant.name:
            extensions = [''] + [f' ({tag})' for tag in tags]

        return extensions

    async def reasons_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str,
            *,
            exclude_categories: Optional[list[str]] = None,
            include_categories: Optional[list[str]] = None,
            escalated_categories: Optional[list[str]] = None
    ) -> list[app_commands.Choice[str]]:
        categories = self._get_filtered_categories(exclude_categories, include_categories)
        stripped_current = current.strip()
        escalated_categories = escalated_categories or []

        if not stripped_current:
            base_choices = [
               app_commands.Choice(
                   name="Доступные категории: (введите вручную одну из них)",
                   value='not_pick'
               )
            ] + [
               app_commands.Choice(name=cat, value=f'not_pick:{cat}')
               for cat in categories
            ]
            return base_choices + self._generate_choices(escalated_categories)

        picked_categories = self._get_picked_categories(stripped_current, categories)
        if picked_categories:
            return self._generate_choices(picked_categories)

        all_variants = self._generate_choices(categories) + self._generate_choices(escalated_categories)

        for variant in all_variants:
            if variant.name in stripped_current:
                extensions = self._get_tag_extensions(stripped_current, variant)
                if extensions:
                    return [
                        app_commands.Choice(
                            name=stripped_current + ext,
                            value=stripped_current.replace(variant.name, variant.value) + ext
                        )
                        for ext in extensions
                    ]
                return [
                    app_commands.Choice(
                        name=stripped_current,
                        value=stripped_current.replace(variant.name, variant.value)
                    )
                ]
        return []

    async def warns_autocomplete(self, interaction: discord.Interaction, current: str) -> list[
        app_commands.Choice[str]]:
        return await self.reasons_autocomplete(
            interaction, current,
            include_categories=list(profile_reasons)
        )

    async def text_mutes_autocomplete(self, interaction: discord.Interaction, current: str) -> list[
        app_commands.Choice[str]]:
        return await self.reasons_autocomplete(
            interaction, current,
            exclude_categories=[*profile_reasons, "войс", "текст"],
            escalated_categories=['текст']
        )

    async def voice_mutes_autocomplete(self, interaction: discord.Interaction, current: str) -> list[
        app_commands.Choice[str]]:
        return await self.reasons_autocomplete(
            interaction, current,
            exclude_categories=[*profile_reasons, "войс", "текст"],
            escalated_categories=['войс']
        )

    async def bans_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self.reasons_autocomplete(interaction, current, exclude_categories=list(profile_reasons))
