import logging
from typing import Optional, List, Dict

import discord
from discord.ext import commands

import cogs
from libs.config import config


class Protection(commands.Cog):
    class Moderation(commands.Cog):
        def __init__(self, bot: commands.Bot):
            self.bot = bot
            self.modlog: Optional[cogs.administration.modlog.ModLog] = None
            bot.loop.create_task(self._init())
            self.staff: Optional[discord.Role] = None

        async def _init(self):
            logging.info("[PROTECT] Waiting for bot")
            await self.bot.wait_until_ready()
            self.modlog = self.bot.get_cog("ModLog")
            self.staff = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["staff"])
            logging.info("[PROTECT] Ready")





def setup(bot: commands.Bot) -> None:
    bot.add_cog(Protection(bot))
