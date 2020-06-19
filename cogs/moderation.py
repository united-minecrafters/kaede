from typing import Optional, Union

import discord
from discord.ext import commands
import logging
import cogs


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.modlog.ModLog] = None
        bot.loop.create_task(self._init())

    async def _init(self):
        logging.info("[MOD] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        logging.info("[MOD] Ready")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: Union[discord.Member, discord.User], *, reason: str = None):
        self.modlog.kaede_bans.append(user.id)
        if isinstance(user, discord.Member):
            await user.ban(reason=f"{ctx.author} | {reason}")
        else:
            await ctx.guild.ban(user, f"S | {ctx.author} | {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def sban(self, ctx: commands.Context, user: Union[discord.Member, discord.User], *, reason: str = None):
        self.modlog.kaede_bans.append(user.id)
        if isinstance(user, discord.Member):
            await user.ban(reason=f"S | {ctx.author} | {reason}")
        else:
            await ctx.guild.ban(user, f"S | {ctx.author} | {reason}")

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


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Moderation(bot))
