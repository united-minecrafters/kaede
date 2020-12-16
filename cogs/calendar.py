import aiohttp
import asyncio
import logging
import datetime as dt
import pytz
from dataclasses import dataclass
from typing import Dict, Optional

import aiosqlite
import discord
from dateutil.parser import parse
from discord.ext import commands, tasks
from discord.utils import escape_markdown, escape_mentions, find
from disputils import BotMultipleChoice, BotEmbedPaginator, BotConfirmation

import cogs.administration.modlog
from libs.utils import pages, numbered, str_to_stamp, stamp_to_str
from libs.config import config


def sanitize(s):
    return escape_mentions(escape_markdown(s))


sql_string_avails_table = """CREATE TABLE IF NOT EXISTS availabilities (
                             userid INTEGER,
                             date_start REAL,
                             date_end REAL,
                             timezone TEXT
                             );"""

sql_string_events_table = """CREATE TABLE IF NOT EXISTS events (
                             userid INTEGER,
                             date_start REAL,
                             date_end REAL,
                             timezone TEXT,
                             name TEXT,
                             channel_id INTEGER,
                             role_id INTEGER,
                             sent INTEGER
                             );"""


@dataclass
class Availability:
    userid: int
    date_start: float
    date_end: float
    timezone: str


@dataclass
class Event:
    userid: int
    date_start: float
    date_end: float
    timezone: str
    name: str
    channel_id: int
    role_id: int
    sent: int


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.administration.modlog.ModLog] = None
        self.lock = asyncio.Lock()
        self.events = []
        self.timezones: Dict[int, str] = {}
        self.availabilities = []
        bot.loop.create_task(self._init())
        self.end_check.start()

    async def _init(self):
        # load availabilities here
        logging.info("[CAL] Waiting for bot")
        async with aiosqlite.connect('calendar.db') as db:
            await db.execute(sql_string_avails_table)
            await db.execute(sql_string_events_table)
            await db.commit()

            async with db.execute("""SELECT * FROM availabilities""") as cursor:
                avail_rows = await cursor.fetchall()
                if avail_rows:
                    for avail_tup in avail_rows:
                        avail = Availability(userid=avail_tup[0],
                                             date_start=avail_tup[1],
                                             date_end=avail_tup[2],
                                             timezone=avail_tup[3])
                        self.availabilities.append(avail)
                        if avail_tup[0] not in self.timezones:
                            self.timezones[avail_tup[0]] = avail_tup[3]

            async with db.execute("""SELECT * FROM events""") as cursor:
                event_rows = await cursor.fetchall()
                if event_rows:
                    for event_tup in event_rows:
                        event = Event(userid=event_tup[0],
                                      date_start=event_tup[1],
                                      date_end=event_tup[2],
                                      timezone=event_tup[3],
                                      name=event_tup[4],
                                      channel_id=event_tup[5],
                                      role_id=event_tup[6],
                                      sent=event_tup[7])
                        self.events.append(event)
                        if event_tup[0] not in self.timezones:
                            self.timezones[event_tup[0]] = event_tup[3]

        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        logging.info("[CAL] Ready")

    @tasks.loop(seconds=10)
    async def end_check(self):
        async with self.lock:
            for n, avail in enumerate(self.availabilities):
                offset = dt.datetime.now(pytz.timezone(avail.timezone)).utcoffset().total_seconds()
                utc = dt.datetime.utcnow() + dt.timedelta(seconds=offset)
                date_end = dt.datetime.fromtimestamp(avail.date_end)
                if utc > date_end:
                    async with aiosqlite.connect("calendar.db") as db:
                        await db.execute(
                            """DELETE FROM availabilities WHERE userid=? AND date_start=? AND date_end=?""",
                            (avail.userid, avail.date_start, avail.date_end))
                        await db.commit()
                    self.availabilities[n] = None
            self.availabilities = [avail for avail in self.availabilities if avail is not None]

        for event in self.events:
            guild = self.bot.get_guild(586199960198971409)
            offset = dt.datetime.now(pytz.timezone(event.timezone)).utcoffset().total_seconds()
            utc = dt.datetime.utcnow() + dt.timedelta(seconds=offset)
            date_start = dt.datetime.fromtimestamp(event.date_start)
            if date_start < utc and event.sent == 0:
                embed = discord.Embed(title=f"{event.name} event has started!",
                                      colour=0x94F29B)
                embed.add_field(name=f"Start: {stamp_to_str(event.date_start)}",
                                value=f"**End: {stamp_to_str(event.date_end)}**")
                channel = find(lambda x: x == int(event.channel_id),
                               [TextChannel.id for TextChannel in guild.text_channels])
                await guild.get_channel(channel).send(f"<@&{event.role_id}>", embed=embed)
                event.sent = 1
                async with aiosqlite.connect("calendar.db") as db:
                    await db.execute("""UPDATE events SET sent=?
                                        WHERE userid=? AND date_start=? AND date_end=? AND name=?""",
                                     (1, event.userid, event.date_start, event.date_end, event.name))
                    await db.commit()

        async with self.lock:
            for n, event in enumerate(self.events):
                offset = dt.datetime.now(pytz.timezone(event.timezone)).utcoffset().total_seconds()
                utc = dt.datetime.utcnow() + dt.timedelta(seconds=offset)
                date_end = dt.datetime.fromtimestamp(event.date_end)
                if utc > date_end:
                    async with aiosqlite.connect("calendar.db") as db:
                        await db.execute("""DELETE FROM events
                                            WHERE userid=? AND date_start=? AND date_end=? AND name=?""",
                                         (event.userid, event.date_start, event.date_end, event.name))
                        await db.commit()
                        self.events[n] = None
                self.events = [event for event in self.events if event is not None]

    @commands.command(name="availability", aliases=["avail"])
    async def set_availability(self, ctx: commands.Context, date: str, start: str, end: str):
        """
        Set's a user's availability
        Set date as: day/month/year
        Set start & end in 24 hour format
        """
        if parse(start) > parse(end):
            await ctx.send(embed=discord.Embed(title='The start time must be before the end time',
                                               colour=0xFF0000))
            return
        if ctx.author.id in self.timezones:
            user_tz = self.timezones[ctx.author.id]
        else:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://www.ansura.xyz/api/{ctx.author.id}") as resp:
                    if resp.status != 200:
                        await ctx.send(embed=discord.Embed(title="You don't have a timezone set with Ansura",
                                                           description="Do `%help` to see Ansura's commands",
                                                           colour=0xFF0000))
                        return
                    else:
                        js = await resp.json()
            user_tz = js["timezone"]
            self.timezones[ctx.author.id] = user_tz
        date_start = str_to_stamp(date, start)
        date_end = str_to_stamp(date, end)
        avail = Availability(userid=ctx.author.id, date_start=date_start,
                             date_end=date_end, timezone=user_tz)
        async with self.lock:
            self.availabilities.append(avail)
        async with aiosqlite.connect("calendar.db") as db:
            await db.execute("""INSERT INTO availabilities (userid, date_start, date_end, timezone)
                                VALUES (?,?,?,?)""",
                             (ctx.author.id, date_start, date_end, user_tz,))
            await db.commit()
        await ctx.send(embed=discord.Embed(title=f"Availability set for {ctx.author.display_name}",
                                           description=f"Set as: {stamp_to_str(date_start)} - "
                                                       f"{stamp_to_str(date_end)}",
                                           colour=0x94F29B))

    @commands.command(name="va")
    async def view_availabilities(self, ctx: commands.Context):
        """
        View all availabilities or the ones for a specific user
        """
        if not self.availabilities:
            await ctx.send(embed=discord.Embed(title='No availabilities have been set!',
                                               colour=0xFF0000))
            return
        choice_list = list(set([ctx.guild.get_member(avail.userid).display_name for avail in self.availabilities]))
        multiple_choice = BotMultipleChoice(
            ctx, choice_list, "Choose a user to view availabilities for",
            colour=0x94F29B)
        await multiple_choice.run()
        await multiple_choice.quit()
        e_avails = discord.Embed(title=f'{multiple_choice.choice}\'s availabilities',
                                 colour=0x94F29B)
        if multiple_choice.choice:
            for avail in self.availabilities:
                if ctx.guild.get_member(avail.userid).display_name == multiple_choice.choice:
                    e_avails.add_field(name=f'Start: {stamp_to_str(avail.date_start)}',
                                       value=f'**End: {stamp_to_str(avail.date_end)}**')
            await ctx.send(embed=e_avails)

    @commands.command(name='delavail')
    async def delete_availabilities(self, ctx: commands.Context):
        if not self.availabilities:
            await ctx.send(embed=discord.Embed(title='No availabilities have been set!', colour=0xFF0000))
            return
        gen = [
            stamp_to_str(avail.date_start) + " - " + stamp_to_str(avail.date_end)
            for avail in self.availabilities if avail.userid == ctx.author.id
        ]
        multiple_choice = BotMultipleChoice(
            ctx, gen, 'Choose which of your avails to delete',
            colour=0x94F29B)
        await multiple_choice.run()
        await multiple_choice.quit()
        if multiple_choice.choice:
            confirmation = BotConfirmation(ctx, 0x012345)
            await confirmation.confirm(f"Are you sure you want to delete {multiple_choice.choice}?")
            if confirmation.confirmed:
                await confirmation.update("Confirmed", color=0x55ff55)
                async with self.lock:
                    for n, avail in enumerate(self.availabilities):
                        if (stamp_to_str(avail.date_start) + " - " + stamp_to_str(avail.date_end) ==
                                multiple_choice.choice and avail.userid == ctx.author.id):
                            self.availabilities[n] = None
                            async with aiosqlite.connect("calendar.db") as db:
                                await db.execute(
                                    """DELETE FROM availabilities WHERE userid=? AND date_start=? AND date_end=?""",
                                    (ctx.author.id, avail.date_start, avail.date_end))
                                await db.commit()
                    self.availabilities = [avail for avail in self.availabilities if avail is not None]
            else:
                await confirmation.update("Not confirmed", hide_author=True, color=0xFF0000)

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def availabilities(self, ctx: commands.Context, member: discord.Member):
        """
        Shows the availabilities of a user
        #STAFF
        """
        gen = [
            stamp_to_str(avail.date_start) + " - " + stamp_to_str(avail.date_end)
            for avail in self.availabilities if avail.userid == member.id
        ]
        await (BotEmbedPaginator(ctx, pages(numbered(
            gen),
            n=10, title=f'{member.display_name}\'s availabilities'))).run()

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def upcoming(self, ctx: commands.Context, date: str = None):
        """
        View upcoming availabilities for a week
        Can optionally specify a date to look up avails for said date
        Input date as: day/month/year
        #STAFF
        """
        if date is None:
            gen_week = [
                (ctx.guild.get_member(avail.userid).display_name + ":\n" + stamp_to_str(avail.date_start) + " - " +
                 stamp_to_str(avail.date_end))
                for avail in self.availabilities
                if (dt.datetime.fromtimestamp(avail.date_start) < dt.datetime.utcnow() + dt.timedelta(weeks=1))
            ]
            await (BotEmbedPaginator(ctx, pages(numbered(gen_week), n=10,
                                                title='Availabilities for this week'))).run()
        else:
            gen_date = [
                (ctx.guild.get_member(avail.userid).display_name + ":\n" + stamp_to_str(avail.date_start) + " - " +
                 stamp_to_str(avail.date_end))
                for avail in self.availabilities
                if (dt.datetime.fromtimestamp(avail.date_start).strftime("%Y-%m-%d") ==
                    parse(date, dayfirst=True).strftime("%Y-%m-%d"))
            ]
            await (BotEmbedPaginator(ctx, pages(numbered(
                gen_date),
                n=10, title=f'Availabilities for {parse(date).strftime("%Y-%b-%d")}'))).run()

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def schedule(self, ctx: commands.Context, name: str, date: str, start: str, end: str,
                       channel: discord.TextChannel, role: discord.Role = None):
        """
        Schedule an event
        Set date as: day/month/year
        Set time in 24 hour format
        !schedule <name event> <date> <start> <end> <channel> [role_to_ping]
        [] = optional
        #STAFF
        """
        if ctx.author.id in self.timezones:
            user_tz = self.timezones[ctx.author.id]
        else:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://www.ansura.xyz/api/{ctx.author.id}") as resp:
                    if resp.status != 200:
                        await ctx.send(embed=discord.Embed(title="You don't have a timezone set with Ansura",
                                                           description="Do `%help` to see Ansura's commands",
                                                           colour=0xFF0000))
                        return
                    else:
                        js = await resp.json()
            user_tz = js["timezone"]
            self.timezones[ctx.author.id] = user_tz

        if parse(start) > parse(end):
            await ctx.send(embed=discord.Embed(title='The start time must be before the end time',
                                               colour=0xFF0000))
            return
        date_start = str_to_stamp(date, start)
        date_end = str_to_stamp(date, end)
        confirmation = BotConfirmation(ctx, 0x94F29B)
        await confirmation.confirm(f'Are you sure you want to schedule an event for:'
                                   f"{stamp_to_str(date_start)}"
                                   f" - {stamp_to_str(date_end)}")
        if confirmation.confirmed:
            await confirmation.update("Confirmed", color=0x55ff55)
            event = Event(userid=ctx.author.id, date_start=date_start,
                          date_end=date_end, timezone=user_tz,
                          name=name, channel_id=channel.id,
                          role_id=role.id if role else None, sent=0)
            async with self.lock:
                self.events.append(event)
            async with aiosqlite.connect("calendar.db") as db:
                await db.execute(
                    """INSERT INTO events
                       (userid, date_start, date_end, timezone, name, channel_id, role_id, sent)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (ctx.author.id, date_start, date_end, user_tz, name,
                     channel.id, role.id if role else None, 0))
                await db.commit()
        else:
            await confirmation.update("Not confirmed", hide_author=True, color=0xFF0000)

    @commands.has_role(config()["roles"]["staff"])
    @commands.command()
    async def delevent(self, ctx: commands.Context):
        """
        Deletes an event
        #STAFF
        """
        gen = [
            event.name
            for event in self.events
        ]
        multiple_choice = BotMultipleChoice(
            ctx, gen, "Choose which event to delete", colour=0x94F29B)
        await multiple_choice.run()
        await multiple_choice.quit()
        if multiple_choice.choice:
            confirmation = BotConfirmation(ctx, 0x012345)
            await confirmation.confirm(f"Are you sure you want to delete {multiple_choice.choice}?")
            if confirmation.confirmed:
                await confirmation.update("Confirmed", color=0x55ff55)
                async with self.lock:
                    for n, event in enumerate(self.events):
                        if event.name == multiple_choice.choice:
                            self.events[n] = None
                            async with aiosqlite.connect("calendar.db") as db:
                                await db.execute(
                                    """DELETE FROM events WHERE date_start=? AND date_end=? AND name=?""",
                                    (event.date_start, event.date_end, event.name))
                                await db.commit()
                    self.events = [event for event in self.events if event is not None]
            else:
                await confirmation.update("Not confirmed", hide_author=True, color=0xFF0000)

    @commands.command()
    async def events(self, ctx: commands.Context):
        """
        Shows a list of events - maybe show the index delevent would use?
        """
        gen = [
            (event.name, event.date_start, event.date_end,
             event.channel_id, event.role_id, event.timezone)
            for event in self.events
        ]
        if not gen:
            await ctx.send(embed=discord.Embed(title="No events set!",
                                               colour=0xFF0000))
            return
        embeds = []
        for event_tup in gen:
            embed = discord.Embed(title=event_tup[0],
                                  description=f"Start: {stamp_to_str(event_tup[1])}\n"
                                              f"End: {stamp_to_str(event_tup[2])}",
                                  color=0x94F29B)
            embed.add_field(name="Channel to notify:", value=f"<#{event_tup[3]}>")
            embed.add_field(name="Role to ping:", value=f"<@&{event_tup[4]}>")
            embed.add_field(name="Timezone:", value=event_tup[5])
            embeds.append(embed)
        await BotEmbedPaginator(ctx, pages=embeds).run()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Misc(bot))
