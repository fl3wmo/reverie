from typing import TYPE_CHECKING

import cogs.punishments.base as base
import cogs.punishments.mutes as mutes
import cogs.punishments.bans as bans
import cogs.punishments.warns as warns
import cogs.punishments.hides as hides

if TYPE_CHECKING:
    from core.bot import Reverie


async def setup(bot: Reverie):
    cog_list = (base, mutes, bans, warns, hides)
    for cog in cog_list:
        await cog.setup(bot)
