import logging
from typing import Optional, Union

import discord
from discord.ext import commands

import cogs.administration.modlog
from libs.config import config
from libs.conversions import TimeDelta


class Server(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.administration.modlog.ModLog] = None
        bot.loop.create_task(self._init())
        self.staff: Optional[discord.Role] = None
        self.jr_mod: Optional[discord.Role] = None
        self.mod: Optional[discord.Role] = None
        self.admin: Optional[discord.Role] = None
        self.owner: Optional[discord.Role] = None

    async def _init(self):
        logging.info("[SERVER] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        self.staff = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["staff"])
        self.jr_mod = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["jr_mod"])
        self.mod = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["mod"])
        self.admin = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["admin"])
        self.owner = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["owner"])
        logging.info("[SERVER] Ready")

    @commands.has_role(config()["roles"]["jr_mod"])
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.command(aliases=["sm", "slow"])
    async def slowmode(self, ctx: commands.Context, time: str):
        """
        Sets the slowmode on a channel
        Jr Mod and up
        #STAFF
        """
        try:
            t = TimeDelta.parse(time)
        except ValueError:
            raise commands.BadArgument("Invalid time")
        if not 0 <= t.total_seconds() < 21600:
            raise commands.BadArgument("Time must be less than 6h")
        chan: discord.TextChannel = ctx.channel
        old = TimeDelta.from_seconds(chan.slowmode_delay)
        await chan.edit(reason=str(ctx.author), slowmode_delay=t.total_seconds())
        await ctx.send(f"Slowmode chaned to {t}")
        await self.modlog.log_message(title="Slowmode changed",
                                      message=f"Slowmode in {chan.mention} changed from {old} "
                                              f"to {t} by {ctx.author.mention}",
                                      emoji=":clock1:")

    @commands.has_role(config()["roles"]["mod"])
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.command(aliases=["bit", "br"])
    async def bitrate(self, ctx: commands.Context, rate: int, *, channel: Optional[Union[discord.VoiceChannel, str]]):
        """
        Sets the bitrate on a channel
        `!bitrate 40 channelname`
        Mod and up
        #STAFF
        """
        if ctx.author.voice.channel:
            channel = ctx.author.voice.channel
        if rate > 128:
            raise commands.BadArgument("Bitrate must be under 128 and over 8")
        if isinstance(channel, str):
            vc: discord.VoiceChannel
            for vc in ctx.guild.voice_channels:
                if channel.lower() in vc.name.lower():
                    channel = vc
                    break
            else:
                raise commands.BadArgument("Voice channel not found")
        old = channel.bitrate
        try:
            await channel.edit(reason=str(ctx.author), bitrate=rate * 1000)
        except discord.HTTPException as e:
            await ctx.send("An error occurred while executing the command")
            raise e
        await ctx.send(f"Bitrate changed to {rate}kbps in {channel.name}")
        await self.modlog.log_message(title="Bitrate changed",
                                      message=f"Bitrate in {channel.name} changed from {old / 1000}kbps "
                                              f"to {rate}kbps by {ctx.author.mention}",
                                      emoji=":loudspeaker:")

    @commands.has_role(config()["roles"]["mod"])
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.command(aliases=["maxusers"])
    async def max(self, ctx: commands.Context, num: int, *, channel: Optional[Union[discord.VoiceChannel, str]]):
        """
        Sets the user limit on a channel
        `!max 40 channelname`
        Mod and up
        #STAFF
        """
        if ctx.author.voice.channel:
            channel = ctx.author.voice.channel
        if num > 99 or num < 0:
            raise commands.BadArgument("Bitrate must be between 0 and 99, inclusive")
        if isinstance(channel, str):
            vc: discord.VoiceChannel
            for vc in ctx.guild.voice_channels:
                if channel.lower() in vc.name.lower():
                    channel = vc
                    break
            else:
                raise commands.BadArgument("Voice channel not found")
        old = channel.user_limit
        try:
            await channel.edit(reason=str(ctx.author), user_limit=num)
        except discord.HTTPException as e:
            await ctx.send("An error occurred while executing the command")
            raise e
        await ctx.send(f"User limit changed to {num}kbps in {channel.name}")
        await self.modlog.log_message(title="User limit changed",
                                      message=f"User limit in {channel.name} changed from {old}kbps "
                                              f"to {num}kbps by {ctx.author.mention}",
                                      emoji=":loudspeaker:")

    @commands.has_role(config()["roles"]["admin"])
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.command(aliases=["rench"])
    async def renamechannel(self, ctx: commands.Context, channel: discord.TextChannel, *, name: str):
        """
        Rename a text channel
        Admin+
        #STAFF
        """
        if len(name) > 32 or len(name) == 0:
            raise commands.BadArgument("Invalid name")
        old: str = channel.name
        await channel.edit(reason=str(ctx.author), name=name)
        await ctx.send(f"{channel.mention}'s name changed from {old} to {channel.name}")
        await self.modlog.log_message(title="Channel name changed",
                                      message=f"{channel.mention}'s name changed from {old} to {channel.name} "
                                              f"by {ctx.author.mention}")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Server(bot))
