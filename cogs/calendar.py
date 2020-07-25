import logging
from typing import Optional

from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

import cogs.administration.modlog


def sanitize(s):
    return escape_mentions(escape_markdown(s))


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.administration.modlog.ModLog] = None
        bot.loop.create_task(self._init())

    async def _init(self):
        logging.info("[CAL] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        logging.info("[CAL] Ready")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Misc(bot))