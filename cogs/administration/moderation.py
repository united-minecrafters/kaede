import logging
from typing import Optional, Union
import datetime

import discord
from discord.ext import commands
from disputils import BotEmbedPaginator

import cogs
from libs.config import config
from libs.utils import trash_reaction, pages
from cogs.administration.punishments import Record

MOD_HELP_STR = f"""
**kick**
> `!kick @member|ID [reason]`
> Requires `kick_members` permission
> Silent version - `!skick`
_ _
**ban**
> `!ban @member|ID [reason]`
> Requires `ban_members` permission
> Silent version - `!sban`
_ _
**softban**
> `!softban @member|ID [reason]`
> Requires `kick_members` permission
> Bans a member, deleting their messages from the last 7 days
> Silent
_ _
`[]` signifies an *optional* parameter
`|` signifies one OR the other
_ _
Non-silent mod logs go to <#{config()["channels"]["log"]}> with basic info
All mod logs go to <#{config()["channels"]["modlog"]}> with detailed info
"""


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.administration.modlog.ModLog] = None
        self.punishments: Optional[cogs.administration.punishments.Punishments] = None
        bot.loop.create_task(self._init())
        self.user_cache = {}

    async def _init(self):
        logging.info("[MOD] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        self.punishments = self.bot.get_cog("Punishments")
        logging.info("[MOD] Ready")

    @commands.command()
    @commands.has_role(config()["roles"]["staff"])
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        Warns a user, optional reason
        #STAFF
        """
        await self.punishments.insert_warn_record(Record(
            reason=reason,
            user=member.id,
            staff=ctx.author.id
        ))
        await ctx.send(f"{member} warned", delete_after=60)
        await self.modlog.log_warn_action(member, staff=ctx.author, reason=reason)

    @commands.command(aliases=["warns"])
    async def warnlog(self, ctx: commands.Context, member: discord.Member):
        """
        Gets the warnings for a user
        #STAFF
        """
        warns = await self.punishments.get_warn_records(member.id)
        if not warns:
            await ctx.send(embed=discord.Embed(title=f"{member}'s warns", description="No warnings for this member"))
            return
        await BotEmbedPaginator(ctx, pages([
            f"**W-{w.id}** - {w.reason[:100]}\n"
            f"- <@{w.staff}> - "
            f" {datetime.datetime.utcfromtimestamp(w.timestamp).strftime('%b %d %y %H:%M:%S')}"
            for w in warns], 5, f"{member}'s Warns", fmt="%s")).run()

    @commands.command(aliases=["recs"])
    async def records(self, ctx: commands.Context, member: Union[discord.Member, discord.User, int]):

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        self.modlog.kaede_kicks.append(member.id)
        await member.kick(reason=reason)
        await self.modlog.log_kick_action(member, reason=reason, staff=ctx.author)
        await ctx.send(f"`{member}` Kicked")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def skick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        self.modlog.kaede_kicks.append(member.id)
        await member.kick(reason=reason)
        await self.modlog.log_kick_action(member, silent=True, reason=reason, staff=ctx.author)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: Union[discord.Member, int], *, reason: str = None):
        if isinstance(user, int):
            try:
                if user in self.user_cache:
                    user = self.user_cache[user]
                else:
                    user = await self.bot.fetch_user(user)
                    self.user_cache[user] = user
            except discord.NotFound:
                await ctx.send("That ID wasn't found")
                return
            except discord.HTTPException as e:
                await ctx.send(f"An error occurred while banning - {e}")
                return
        self.modlog.kaede_bans.append(user.id)
        await self.modlog.log_ban_action(user, reason=reason, banned=True, staff=ctx.author)
        await self.punishments.insert_ban_record(Record(
            reason=reason, user=user.id, staff=ctx.author.id
        ))
        if isinstance(user, discord.Member):
            await user.ban(reason=f"{ctx.author} | {reason}")
        else:
            await ctx.guild.ban(user, reason=f"S | {ctx.author} | {reason}")
            await ctx.send(f"`{user}` banned")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def sban(self, ctx: commands.Context, user: Union[discord.Member, int], *, reason: str = None):
        if isinstance(user, int):
            try:
                if user in self.user_cache:
                    user = self.user_cache[user]
                else:
                    user = await self.bot.fetch_user(user)
                    self.user_cache[user] = user
            except discord.NotFound:
                await ctx.send("That ID wasn't found")
                return
            except discord.HTTPException as e:
                await ctx.send(f"An error occurred while banning - {e}")
                return
        self.modlog.kaede_bans.append(user.id)
        await self.modlog.log_ban_action(user, reason=reason, silent=True, banned=True, staff=ctx.author)
        if isinstance(user, discord.Member):
            await user.ban(reason=f"S | {ctx.author} | {reason}")
        else:
            await ctx.guild.ban(user, reason=f"S | {ctx.author} | {reason}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        await member.send(f"You have been softbanned from {ctx.guild.name}. This is not a ban, but a kick+message "
                          f"delete.")
        self.modlog.kaede_bans.append(member.id)
        await member.ban(reason=f"{ctx.author} | Soft Ban", delete_message_days=7)
        self.modlog.kaede_unbans.append(member.id)
        await member.unban(reason=f"{ctx.author} | Soft Ban")
        await self.modlog.log_ban_action(member, soft=True, silent=True, staff=ctx.author, reason=reason)

    @commands.command()
    @commands.has_role(config()["roles"]["staff"])
    async def modhelp(self, ctx: commands.Context):
        msg: discord.Message = await ctx.send(
            embed=discord.Embed(
                title="United Minecrafters Moderation Commands",
                description=MOD_HELP_STR
            )
        )
        await trash_reaction(msg, self.bot, ctx)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Moderation(bot))
