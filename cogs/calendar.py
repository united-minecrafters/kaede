import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import discord
from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

import cogs.administration.modlog
from libs.config import config


def sanitize(s):
    return escape_mentions(escape_markdown(s))


@dataclass
class Availability:
    day: Tuple[int, int, int]  # day month year
    start: Tuple[int, int]  # hour minute
    end: Tuple[int, int]  # hour minute

@dataclass
class Event:
    day: Tuple[int, int, int]  # day month year
    start: Tuple[int, int]  # hour minute
    end: Tuple[int, int]  # hour minute


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.administration.modlog.ModLog] = None

        self.events: List[Event] = []

        self.availabilities: Dict[int, List[Availability]] = {}
        # this could be a Dictionary, indexed by userid, with
        #  the values being a list of availabilities

        bot.loop.create_task(self._init())

    async def _init(self):
        # load availabilities here
        logging.info("[CAL] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        logging.info("[CAL] Ready")

    @commands.command(name="availability", aliases=["avail"])
    async def set_availability(self, ctx: commands.Context, date: str, start: str, end: str):
        """
        Set's a user's availability
        """
        # maybe allow formats of xx/xx 02:00 04:00? and others?
        pass

    @commands.command(name="va")
    async def view_availabilities(self, ctx: commands.Context):
        """
        View a user's availability
        """
        # disputils has a multiple choice embed?
        pass

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def availabilities(self, ctx: commands.Context, member: discord.Member):
        """
        Shows the availabilities of a user
        #STAFF
        """
        pass

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def upcoming(self, ctx: commands.Context):
        """
        View upcoming availabilities
        #STAFF
        """
        # disputils paginator?
        # could also change to (self, ctx: commands.Context, date: str = None) to
        #  allow optionally looking up a date?
        pass

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def schedule(self, ctx: commands.Context, date: str, time: str, end_time: str):
        """
        Schedule an event
        #STAFF
        """
        # maybe use disputils confirmation on this
        pass

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def delevent(self, ctx: commands.Context, event_number: int):
        """
        Deletes an event
        #STAFF
        """
        # use disputils confirmation on this
        pass

    @commands.command()
    async def events(self, ctx: commands.Context):
        """
        Shows a list of events - maybe show the index delevent would use?
        """
        pass


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Misc(bot))
