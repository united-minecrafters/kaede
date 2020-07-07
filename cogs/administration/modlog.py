import logging
from datetime import datetime
from typing import Optional, Union

import discord
from discord.ext import commands

from libs.config import config
from libs.utils import quote, trim


class ModLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logchannel: Optional[discord.TextChannel] = None
        self.modchannel: Optional[discord.TextChannel] = None
        self.suppressed_deletion_messages = []
        self.kaede_kicks = []
        self.kaede_bans = []
        self.kaede_unbans = []
        bot.loop.create_task(self._init())

    async def _init(self):
        logging.info("[MODLOG] Waiting for bot")
        await self.bot.wait_until_ready()
        self.logchannel = self.bot.get_channel(config()["channels"]["log"])
        self.modchannel = self.bot.get_channel(config()["channels"]["modlog"])
        logging.info("[MODLOG] Ready")

    async def log_message(self, author: discord.Member, title: str, message: str):
        await self.logchannel.send(
            embed=discord.Embed(
                title=title,
                description=message,
                colour=0x00ffff
            ).set_author(name=f"{author} | {author.id}")
        )

    async def log_edit(self, before: discord.Message, after: discord.Message):
        msg = await self.logchannel.send(
            embed=discord.Embed(
                title=f":pencil: Message Edited in #{before.channel.name}",
                description=f"{before.author} | {before.author.id}\n"
                            f"[Jump to message]({before.jump_url})",
                colour=discord.Colour.blue()
            )
                .add_field(name="Before", value=trim(before.content))  # noqa 141
                .add_field(name="After", value=trim(after.content))
        )
        logging.log(15, f"[MODLOG | EDIT] {msg.id}\n---\n{quote(before.content)}\n---\n{quote(after.content)}")

    async def log_filter(self, flt: str, message: discord.Message):
        msg = await self.logchannel.send(
            embed=discord.Embed(
                title=f":warning: Message Filtered in #{message.channel.name}",
                description=f"{message.author} | {message.author.id}\n",
                colour=discord.Colour.orange()
            )
                .add_field(name="Content", value=trim(message.content))  # noqa 141
                .set_footer(text=f"Rule: {flt}")
        )
        self.suppressed_deletion_messages.append(message.id)
        logging.log(15, f"[MODLOG | FILTER] {msg.id} A:{message.author.id} R:{flt} {message.content}")

    async def log_delete(self, message: discord.Message):
        if message.id in self.suppressed_deletion_messages:
            del self.suppressed_deletion_messages[self.suppressed_deletion_messages.index(message.id)]
            return
        if config()["logging"]["ignore_bot"] == 1 and message.author.bot:
            return
        for i in config()["logging"]["ignore_del_prefix"]:
            if message.content.startswith(i):
                return
        msg = await self.logchannel.send(
            embed=discord.Embed(
                title=f":wastebasket: Message Deleted in #{message.channel.name}",
                description=f"{message.author} | {message.author.id}\n",
                colour=discord.Colour.blue(),
                timestamp=message.created_at
            )
                .add_field(name="Content", value=trim(message.content))  # noqa 141
                .set_footer(text="Send time")
        )
        logging.log(15, f"[MODLOG | DELETE] {msg.id}: {msg.content}")

    async def log_user(self, member: Union[discord.Member, discord.User], join: bool):
        typ = "Bot" if member.bot else "User"
        st = "joined" if join else "left"
        emoji = "smile" if join else "frowning"
        msg = await self.logchannel.send(
            embed=discord.Embed(
                title=f":{emoji}: {typ} {st}",
                description=f"<@!{member.id}> `{member}`",
                colour=discord.Colour.purple()
            )
                .add_field(name="ID", value=str(member.id))  # noqa 141
                .add_field(name="Joined Server", value=datetime.now().isoformat(), inline=False)
                .add_field(name="Joined Discord", value=member.created_at.isoformat(), inline=False)
        )
        logging.log(15, f"[MODLOG | USER] {msg.id} U:{member.id} JOIN:{join}")

    async def log_kick_action(self, member: Union[discord.Member, discord.User], *,
                              silent: bool = False, reason: str = None, staff: discord.Member = None):
        if not silent:
            await self.modchannel.send(
                embed=discord.Embed(
                    title=f"User Kicked",
                    description=f"{member} | <@!{member.id}>\n",
                    colour=discord.Colour.orange()
                )
            )
        await self.logchannel.send(
            embed=discord.Embed(
                title=f"User Kicked",
                description=f"{member} | <@!{member.id}>",
                colour=discord.Colour.orange()
            )
            .add_field(name="Staff Member", value=f"{staff} | <@!{staff.id}>" if staff else "None", inline=False)
            .add_field(name="Reason", value=reason if reason else "None", inline=False)
        )

    async def log_warn_action(self, member: discord.Member, *, reason: str = None, staff: discord.Member = None):
        await self.logchannel.send(
            embed=discord.Embed(
                title=f"User Warned",
                description=f"{member} | <@!{member.id}>",
                colour=discord.Colour.orange()
            )
            .add_field(name="Staff Member", value=f"{staff} | <@!{staff.id}>" if staff else "None", inline=False)
            .add_field(name="Reason", value=reason if reason else "None", inline=False)
        )

    async def log_ban_action(self, member: Union[discord.Member, discord.User], *,
                             soft: bool = False, silent: bool = False, reason: str = None,
                             banned: bool = False, staff: discord.Member = None):
        action = "Soft-Banned" if soft else (" Banned" if banned else "Unbanned")
        emoji = ":shushing_face:" if soft else (":no_entry_sign:" if banned else ":green_circle:")
        if not silent:
            await self.modchannel.send(
                embed=discord.Embed(
                    title=f"{emoji} User {action}",
                    description=f"{member} | <@!{member.id}>\n",
                    colour=discord.Colour.orange()
                )
            )
        await self.logchannel.send(
            embed=discord.Embed(
                title=f"User {action}",
                description=f"{member} | <@!{member.id}>",
                colour=discord.Colour.orange()
            )
            .add_field(name="Staff Member", value=f"{staff} | <@!{staff.id}>" if staff else "None", inline=False)
            .add_field(name="Reason", value=reason if reason else "None", inline=False)
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content:
            await self.log_edit(before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        await self.log_delete(message)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.log_user(member, True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.log_user(member, False)

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: Union[discord.User, discord.Member]):
        reason, staff, silent = None, None, False
        if user.id in self.kaede_bans:
            del self.kaede_bans[self.kaede_bans.index(user.id)]
            return
        await self.log_ban_action(user, reason=reason, banned=True, staff=staff)

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: Union[discord.User, discord.Member]):
        reason, staff, silent = None, None, False
        if user.id in self.kaede_unbans:
            del self.kaede_unbans[self.kaede_unbans.index(user.id)]
            return
        await self.log_ban_action(user, reason=reason, staff=staff)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ModLog(bot))
