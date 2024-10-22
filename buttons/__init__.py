from discord.ext import commands

import buttons.roles
import buttons.punishments
import buttons.online
from buttons.roles import roles_check, roles_take, roles_review
from buttons.punishments import punishment_review
from buttons.links import ForumLink

def load_buttons(bot: commands.Bot):
    bot.add_dynamic_items(
        buttons.roles.TakeRole, buttons.roles.ApproveRole, buttons.roles.RejectRole, buttons.roles.ReviewApproveRole, buttons.roles.ReviewPartialApproveRole, buttons.roles.ReviewRejectRole,
        buttons.punishments.ApprovePunishment, buttons.punishments.RejectPunishment,
        buttons.online.OnlineReload
    )