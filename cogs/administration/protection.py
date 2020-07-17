import logging
from typing import Optional

import discord
from discord.ext import commands

import cogs
from libs.config import config, emojis, save_config


class Protection(commands.Cog):
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

    def _get_autokick_emoji(self):
        return emojis.autokick_off if config()["autokick"] == 0 else emojis.autokick_on

    @commands.command(aliases=["ak"])
    @commands.has_role(config()["roles"]["staff"])
    async def autokick(self, ctx: commands.Context, days: int = None):
        """
        Set the threshold age to kick new accounts at
        !ak - shows current state
        !ak 4 - set to 4 days
        !ak 0 - turn off
        #STAFF
        """
        if days is None:
            st = "off" if config()["autokick"] == 0 else f"kicking accounts newer than " \
                                                         f"{config()['autokick']} days"
            await ctx.send(f"{self._get_autokick_emoji()} Autokick is {st}")
            return
        config()['autokick'] = days
        save_config()
        st = "off" if config()["autokick"] == 0 else f"kicking accounts newer than " \
                                                     f"{config()['autokick']} days"
        await ctx.send(f"{self._get_autokick_emoji()} Autokick is {st}")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Protection(bot))
