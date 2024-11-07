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


class RolesetCog(commands.Cog):
    def __init__(self, bot: EsBot):
        self.bot = bot
        self.db = db.roles
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return
        
        old_level = security.user_level(before)
        new_level = security.user_level(after)
        
        if old_level == new_level:
            return
            
        head_mod_levels = [security.PermissionLevel.GMD, security.PermissionLevel.DS]
        is_new_head_mod = new_level in head_mod_levels and old_level not in head_mod_levels
        is_removed_head_mod = new_level not in head_mod_levels and old_level in head_mod_levels and not security.is_in_head_moderation_team(after, self.bot.guilds)
        
        for guild in self.bot.guilds:
            try:
                head_mod_role = security.head_moderation_team(guild)
            except ValueError:
                continue
            
            member = await self.bot.getch_member(guild, after.id)
            if not member:
                continue
                
            if is_new_head_mod and head_mod_role not in member.roles:
                await member.add_roles(head_mod_role)
            elif is_removed_head_mod:
                if head_mod_role in member.roles:
                    await member.remove_roles(head_mod_role)


async def setup(bot: EsBot):
    await bot.add_cog(RolesetCog(bot))
