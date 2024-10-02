import re
from typing import Any

import discord
from discord import Interaction
from discord._types import ClientT

from database import db


class ApprovePunishment(discord.ui.DynamicItem[discord.ui.Button], template='punishments:approve:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label='Одобрить',
                style=discord.ButtonStyle.blurple,
                custom_id=f'punishments:approve:{action_id}',
                emoji='\N{THUMBS UP SIGN}',
            )
        )
        self.action_id: int = action_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        embed = interaction.message.embeds[0]
        embed.colour = discord.Color.green()

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=interaction.user.display_name, emoji='\N{THUMBS UP SIGN}', disabled=True))
        await db.actions.approve(self.action_id, interaction.user.id)
        
        await interaction.message.edit(embed=embed, view=view)
        await interaction.response.defer(ephemeral=True)
        

class RejectPunishment(discord.ui.DynamicItem[discord.ui.Button], template='punishments:reject:(?P<id>[0-9]+)'):
    def __init__(self, action_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label='Отказать',
                style=discord.ButtonStyle.red,
                custom_id=f'punishments:reject:{action_id}',
                emoji='\N{THUMBS DOWN SIGN}',
            )
        )
        self.action_id: int = action_id
    
    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        action_id = int(match['id'])
        return cls(action_id)

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        embed = interaction.message.embeds[0]
        embed.colour = discord.Color.red()

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label=interaction.user.display_name, emoji='\N{THUMBS DOWN SIGN}', disabled=True))

        punishments = interaction.client.get_cog('punishments')
        await punishments.revert_action(interaction.user, self.action_id)

        await interaction.message.edit(embed=embed, view=view)
        await interaction.response.defer(ephemeral=True)
        
        
def punishment_review(action_id: int) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(ApprovePunishment(action_id))
    view.add_item(RejectPunishment(action_id))
    return view
