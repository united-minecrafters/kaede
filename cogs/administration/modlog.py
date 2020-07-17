import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Union

import discord
from discord.ext import commands

from libs.config import config, emojis
from libs.conversions import seconds_to_str
from libs.utils import quote, trim

AUTOKICK_STR = "Hey {user}!\n" \
               " Thank you for your interest in {guild}, but unfortunately we are only " \
               "allowing accounts older than {age} days to join. Even so, thanks for joining! Feel free " \
               "to try rejoining in the future."

JOIN_STR = "Welcome to {guild}, {member}!\n" \
           "Be sure to head over to {role_channel} and read the {rules_channel}. Tell us about yourself " \
           "in {intro_channel}. You'll need to get a Minecraft platform role to view most of the server\n\n" \
           "If you are here about the modded server, do `!modded` and it will show you the steps you need " \
           "to do to join. \n" \
           "If you are here about the bedrock server, it's public! Just do `!servers` and grab the IP. \n" \
           "{operator_role}s are here if you have any questions. Have fun!"


class ModLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logchannel: Optional[discord.TextChannel] = None
        self.modchannel: Optional[discord.TextChannel] = None
        self.greeting: Optional[discord.TextChannel] = None
        self.operator: Optional[discord.Role] = None
        self.suppressed_deletion_messages = []
        self.kaede_kicks = []
        self.kaede_bans = []
        self.kaede_unbans = []
        self.suppressed_leaves = []
        bot.loop.create_task(self._init())

    async def _init(self):
        logging.info("[MODLOG] Waiting for bot")
        await self.bot.wait_until_ready()
        self.logchannel = self.bot.get_channel(config()["channels"]["log"])
        self.modchannel = self.bot.get_channel(config()["channels"]["modlog"])
        self.greeting = self.bot.get_channel(config()["channels"]["greeting"])
        self.operator = self.bot.get_guild(586199960198971409).get_role(config()["roles"]["operator"])
        logging.info("[MODLOG] Ready")

    async def log_message(self, title: str, message: str, author: discord.Member = None, emoji: str = None):
        embed = discord.Embed(
            title=f"{emoji} {title}" if emoji else title,
            description=message,
            colour=config()["colors"]["log_message"]
        )
        if author:
            embed.set_author(name=f"{author} | {author.id}")
        await self.logchannel.send(embed=embed)

    async def log_edit(self, before: discord.Message, after: discord.Message):
        msg = await self.logchannel.send(
            embed=discord.Embed(
                title=f"{emojis.edit} Message Edited in #{before.channel.name}",
                description=f"{before.author} | {before.author.id}\n"
                            f"[Jump to message]({before.jump_url})",
                colour=config()["colors"]["edit"]
            )
                .add_field(name="Before", value=trim(before.content))  # noqa 141
                .add_field(name="After", value=trim(after.content))
        )
        logging.log(15, f"[MODLOG | EDIT] {msg.id}\n---\n{quote(before.content)}\n---\n{quote(after.content)}")

    async def log_filter(self, flt: str, message: discord.Message):
        msg = await self.logchannel.send(
            embed=discord.Embed(
                title=f"{emojis.filter} Message Filtered in #{message.channel.name}",
                description=f"{message.author} | {message.author.id}\n",
                colour=config()["colors"]["filter"]
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
                title=f"{emojis.delete} Message Deleted in #{message.channel.name}",
                description=f"{message.author} | {message.author.id}\n",
                colour=config()["colors"]["delete"],
                timestamp=message.created_at
            )
                .add_field(name="Content", value=trim(message.content))  # noqa 141
                .set_footer(text="Send time")
        )
        logging.log(15, f"[MODLOG | DELETE] {msg.id}: {msg.content}")

    async def log_user(self, member: Union[discord.Member, discord.User], join: bool):
        typ = "Bot" if member.bot else "User"
        st = "joined" if join else "left"
        if join:
            embed = discord.Embed(
                title=f"Welcome, {member.display_name}!",
                description=JOIN_STR.format(
                    guild=member.guild.name,
                    member=member.mention,
                    role_channel=f"<#{config()['channels']['roles']}>",
                    rules_channel=f"<#{config()['channels']['rules']}>",
                    intro_channel=f"<#{config()['channels']['intro']}>",
                    operator_role=self.operator.mention
                )
            ).set_thumbnail(url=member.avatar_url)
            await self.greeting.send(member.mention, delete_after=1)
            await self.greeting.send(embed=embed)
        else:
            if member.id in self.suppressed_leaves:
                self.suppressed_leaves.remove(member.id)
                return
            if member.id in self.kaede_bans:
                self.kaede_bans.remove(member.id)
                return
            if member.id in self.kaede_kicks:
                self.kaede_kicks.remove(member.id)
                return
            await self.greeting.send(f"{member.mention} ({member.display_name}) has left the chat.")
        emoji = emojis.user_join if join else emojis.user_leave
        msg = await self.logchannel.send(
            embed=discord.Embed(
                title=f"{emoji} {typ} {st}",
                description=f"<@!{member.id}> `{member}`",
                colour=config()["colors"]["user"]
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
                    title="User Kicked",
                    description=f"{member} | <@!{member.id}>\n",
                    colour=config()["colors"]["kick"]
                )
            )
        await self.logchannel.send(
            embed=discord.Embed(
                title="User Kicked",
                description=f"{member} | <@!{member.id}>",
                colour=config()["colors"]["kick"]
            )
            .add_field(name="Staff Member", value=f"{staff} | <@!{staff.id}>" if staff else "None", inline=False)
            .add_field(name="Reason", value=reason if reason else "None", inline=False)
        )

    async def log_mute_action(self, member: Union[discord.Member, discord.User], *, muted: bool = True,
                              manual: bool = False, seconds: int = None, staff: discord.Member = None,
                              rule: str = None):
        if muted:
            await self.logchannel.send(
                embed=discord.Embed(
                    title=f"{emojis.mute} User Muted",
                    description=f"{member} | <@!{member.id}>",
                    colour=config()["colors"]["mute"]
                )
                .add_field(name="Staff Member", value=f"{staff} | <@!{staff.id}>" if staff else "None",
                           inline=False)
                .add_field(name="Type", value="Manual" if manual else f"Auto {rule}")
                .add_field(name="Time", value=seconds_to_str(seconds) if seconds else "N/A")
            )
        else:
            await self.logchannel.send(
                embed=discord.Embed(
                    title=f"{emojis.un} User Unmuted",
                    description=f"{member} | <@!{member.id}>",
                    colour=config()["colors"]["mute"]
                )
                .add_field(name="Staff Member", value=f"{staff} | <@!{staff.id}>" if staff else "None",
                           inline=False)
                .add_field(name="Type", value="Manual" if manual else "Auto")
            )

    async def log_warn_action(self, member: discord.Member, *, reason: str = None, staff: discord.Member = None):
        await self.logchannel.send(
            embed=discord.Embed(
                title="User Warned",
                description=f"{member} | <@!{member.id}>",
                colour=config()["colors"]["warn"]
            )
            .add_field(name="Staff Member", value=f"{staff} | <@!{staff.id}>" if staff else "None", inline=False)
            .add_field(name="Reason", value=reason if reason else "None", inline=False)
        )

    async def log_ban_action(self, member: Union[discord.Member, discord.User], *,
                             soft: bool = False, silent: bool = False, reason: str = None,
                             banned: bool = False, staff: discord.Member = None):
        action = "Soft-Banned" if soft else (" Banned" if banned else "Unbanned")
        emoji = emojis.softban if soft else (emojis.ban if banned else emojis.unban)
        if not silent:
            await self.modchannel.send(
                embed=discord.Embed(
                    title=f"{emoji} User {action}",
                    description=f"{member} | <@!{member.id}>\n",
                    colour=config()["colors"]["ban"]
                )
            )
        await self.logchannel.send(
            embed=discord.Embed(
                title=f"User {action}",
                description=f"{member} | <@!{member.id}>",
                colour=config()["colors"]["ban"]
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
        if config()["autokick"] > 0:
            now = datetime.utcnow()
            td = timedelta(days=config()["autokick"])
            diff: timedelta = now - member.created_at
            if diff < td:
                try:
                    await member.send(AUTOKICK_STR.format(
                        user=member.mention,
                        guild=member.guild.name,
                        age=config()["autokick"]
                    ))
                except discord.Forbidden:
                    dm_sent = False
                else:
                    dm_sent = True
                await self.log_message("User Denied Entry", f"Member {member} ({member.id}) was denied "
                                                            f"entry because their account was newer than "
                                                            f"{config()['autokick']} days\n"
                                                            f"DM was {'not ' if not dm_sent else ''}sent",
                                       emoji=emojis.autokick_on)
                self.suppressed_leaves.append(member.id)
                await asyncio.sleep(1)
                await member.kick(reason="Autokick enabled, account too new")
                return
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
        await self.log_ban_action(user, reason=reason, banned=True, staff=staff, silent=silent)

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: Union[discord.User, discord.Member]):
        reason, staff, silent = None, None, False
        if user.id in self.kaede_unbans:
            del self.kaede_unbans[self.kaede_unbans.index(user.id)]
            return
        await self.log_ban_action(user, reason=reason, staff=staff, silent=silent)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ModLog(bot))
