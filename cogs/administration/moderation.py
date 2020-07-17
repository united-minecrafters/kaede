import asyncio
import datetime
import logging
from copy import copy
from typing import Dict, List, Optional, Union

import discord
from discord.ext import commands
from disputils import BotEmbedPaginator

import cogs
from cogs.administration.punishments import Record
from libs.config import config
from libs.utils import pages, trash_reaction

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
        self.active_mutes: List[int] = []
        self.muted_role: Optional[discord.Role] = None
        self.staff: Optional[discord.Role] = None
        self.overwrite_restore: Dict[int, Optional[bool]] = {}

    async def _init(self):
        logging.info("[MOD] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        self.punishments = self.bot.get_cog("Punishments")
        self.muted_role = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["muted"])
        self.staff = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["staff"])
        for i in self.muted_role.members:
            self.active_mutes.append(i.id)
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
            for w in warns], 8, f"{member}'s Warns", fmt="%s")).run()

    @commands.command(aliases=["recs"])
    async def records(self, ctx: commands.Context, member: Union[discord.Member, discord.User, int]):
        """
        Gets the moderation records for a user
        #STAFF
        """
        if not isinstance(member, int):
            member = member.id
        warns = await self.punishments.get_warn_records(member)
        bans = await self.punishments.get_ban_records(member)
        total = warns + bans
        if not total:
            await ctx.send(embed=discord.Embed(title=f"{member}'s warns", description="No records for this member"))
            return
        await BotEmbedPaginator(ctx, pages([
            f"**{w.typ}-{w.id}** - {w.reason[:100]}\n"
            f"- <@{w.staff}> - "
            f" {datetime.datetime.utcfromtimestamp(w.timestamp).strftime('%b %d %y %H:%M:%S')}"
            for w in sorted(total, key=lambda x: x.timestamp)], 8, f"{member}'s Records", fmt="%s")).run()

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        #STAFF
        """
        self.modlog.kaede_kicks.append(member.id)
        await member.kick(reason=reason)
        await self.modlog.log_kick_action(member, reason=reason, staff=ctx.author)
        await ctx.send(f"`{member}` Kicked")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def skick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        #STAFF
        """
        self.modlog.kaede_kicks.append(member.id)
        await member.kick(reason=reason)
        await self.modlog.log_kick_action(member, silent=True, reason=reason, staff=ctx.author)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: Union[discord.Member, int], *, reason: str = None):
        """
        #STAFF
        """
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
        """
        #STAFF
        """
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
        """
        #STAFF
        """
        await member.send(f"You have been softbanned from {ctx.guild.name}. This is not a ban, but a kick+message "
                          f"delete.")
        self.modlog.kaede_bans.append(member.id)
        await member.ban(reason=f"{ctx.author} | Soft Ban", delete_message_days=7)
        self.modlog.kaede_unbans.append(member.id)
        await member.unban(reason=f"{ctx.author} | Soft Ban")
        await self.modlog.log_ban_action(member, soft=True, silent=True, staff=ctx.author, reason=reason)

    @commands.command(aliases=["mhelp"])
    @commands.has_role(config()["roles"]["staff"])
    async def modhelp(self, ctx: commands.Context):
        """
        #STAFF
        """
        msg: discord.Message = await ctx.send(
            embed=discord.Embed(
                title="United Minecrafters Moderation Commands",
                description=MOD_HELP_STR
            )
        )
        await trash_reaction(msg, self.bot, ctx)

    @commands.command()
    @commands.has_role(config()["roles"]["staff"])
    async def mute(self, ctx: commands.Context, user: discord.Member):
        """
        Indefinitely mutes a user
        #STAFF
        """
        if user.id in self.active_mutes:
            await ctx.send(f"{user} is already muted.")
            return
        self.active_mutes.append(user.id)
        await user.add_roles(ctx.guild
                             .get_role(int(config()["roles"]["muted"])), reason=f"Muted by {ctx.author}")
        await self.modlog.log_mute_action(user, manual=True, seconds=0, staff=ctx.author)
        await self.punishments.insert_warn_record(Record(
            reason="Mute",
            user=user.id,
            staff=ctx.author.id
        ))
        await ctx.send(f"Muted {user}")

    @commands.command()
    @commands.has_role(config()["roles"]["staff"])
    async def unmute(self, ctx: commands.Context, user: discord.Member):
        """
        Unmutes a user
        #STAFF
        """
        if user.id not in self.active_mutes:
            await ctx.send(f"{user} is not muted.")
            return
        del self.active_mutes[self.active_mutes.index(user.id)]
        await user.remove_roles(ctx.guild
                                .get_role(int(config()["roles"]["muted"])), reason=f"Unmuted by {ctx.author}")
        await self.modlog.log_mute_action(user, muted=False, manual=True, seconds=0, staff=ctx.author)
        await ctx.send(f"Unmuted {user}")

    @commands.command(aliases=["silence"])
    @commands.has_role(config()["roles"]["staff"])
    async def sh(self, ctx: commands.Context, time: int = 10):
        """
        Silences a channel, so that only staff can speak. The default time is 10m
        #STAFF
        """
        if time <= 0: time = 10
        if await self.silence_channel(ctx.channel):
            await self.modlog.log_message("Channel silenced", f"Channel <#{ctx.channel.id}> silenced", ctx.author)
            s = f" for {time}m" if time else ""
            await ctx.send(f"Channel silenced{s}")
            await asyncio.sleep(time*60)
            await self.unsilence_channel(ctx.channel)
            await ctx.send(f"Channel unsilenced")
            await self.modlog.log_message("Channel unsilenced", f"Channel <#{ctx.channel.id}> unsilenced", ctx.author)

    @commands.command(aliases=["unsilence"])
    @commands.has_role(config()["roles"]["staff"])
    async def unsh(self, ctx: commands.Context):
        """
        Unsilences a channel
        #STAFF
        """
        if await self.unsilence_channel(ctx.channel):
            await self.modlog.log_message("Channel unsilenced", f"Channel <#{ctx.channel.id}> unsilenced", ctx.author)
            await ctx.send("Channel unsilenced")

    async def silence_channel(self, channel: discord.TextChannel):
        if channel.overwrites_for(channel.guild.default_role).send_messages is False:
            await self.modlog.log_message("Channel already silenced", f"Channel <#{channel.id}> already silenced",
                                          channel.guild.me)
            return False
        if channel.category and channel.category.id in config()["restricted_categories"]:
            await self.modlog.log_message("Channel not silenced", f"Channel <#{channel.id}> in a restricted category",
                                          channel.guild.me)
            return False
        self.overwrite_restore[channel.id] = \
            channel.overwrites_for(channel.guild.default_role).send_messages
        perms: discord.PermissionOverwrite = channel.overwrites_for(channel.guild.default_role)
        perms.update(send_messages=False)
        await channel.set_permissions(channel.guild.default_role, overwrite=perms)
        perms: discord.PermissionOverwrite = channel.overwrites_for(self.staff)
        perms.update(send_messages=True)
        await channel.set_permissions(self.staff, overwrite=perms)
        return True

    async def unsilence_channel(self, channel: discord.TextChannel):
        if channel.id not in self.overwrite_restore:
            await self.modlog.log_message("Channel not in overwrite restore",
                                          f"Channel <#{channel.id}> is not in the overwrite restore. It "
                                          f"will have to be unsilenced manually.", channel.guild.me)
            return False
        perms: discord.PermissionOverwrite = channel.overwrites_for(channel.guild.default_role)
        perms.update(send_messages=self.overwrite_restore[channel.id])
        await channel.set_permissions(channel.guild.default_role, overwrite=perms)
        del self.overwrite_restore[channel.id]
        return True

    async def bot_unmute(self, user: discord.Member):
        if user.id not in self.active_mutes:
            return
        del self.active_mutes[self.active_mutes.index(user.id)]
        await user.remove_roles(self.muted_role, reason=f"Unmuted by Bot")
        await self.modlog.log_mute_action(user, muted=False, seconds=0)

    async def bot_mute(self, user: discord.Member, rule: str, seconds: int):
        if user.id in self.active_mutes:
            return False
        self.active_mutes.append(user.id)
        try:
            await user.send("Hey there! Looks like you were muted for spamming. Make sure you refrain from "
                            "that in the future to avoid being kicked or banned.")
        except discord.DiscordException:
            pass
        await self.punishments.insert_warn_record(Record(
            reason=f"Auto Mute - {rule}",
            user=user.id,
            staff=self.bot.user.id
        ))
        await user.add_roles(self.muted_role, reason=f"Muted by Bot")
        await self.modlog.log_mute_action(user, seconds=seconds, rule=rule)
        self.bot.loop.call_later(seconds,
                                 lambda: asyncio.ensure_future(self.bot_unmute(user)))
        return True


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Moderation(bot))
