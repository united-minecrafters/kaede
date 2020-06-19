import logging
import re
from typing import Optional

import discord
from discord.ext import commands

from libs.config import config
from libs.utils import quote
import cogs.modlog

url_regex = re.compile(r"(https?://[^\s]+)")


class Filter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.modlog.ModLog] = None
        bot.loop.create_task(self._init())

    async def _init(self):
        logging.info("[FILTER] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        logging.info("[FILTER] Ready")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content:
            await self.on_message(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        f = config["filters"]
        content = message.content.lower()

        for r in f["role_whitelist"]:
            if r in [a.id for a in message.author.roles[0:1]]:
                pass

        for r in f["word_blacklist"]:
            if re.search(rf"(?:-|\b){r}(?:-|\b)", content):
                try:
                    await message.author.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                              f"blacklisted word. If you feel this was a mistake, let staff know.")
                    await message.author.send(quote(message.content))
                except discord.Forbidden:
                    await message.channel.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                               f"blacklisted word. If you feel this was a mistake, let staff know.")
                await self.modlog.log_filter("word_blacklist", message)
                await message.delete()
                return

        for r in f["token_blacklist"]:
            if re.search(fr"{r}", content):
                try:
                    await message.author.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                              f"blacklisted word. If you feel this was a mistake, let staff know.")
                    await message.author.send(quote(message.content))
                except discord.Forbidden:
                    await message.channel.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                               f"blacklisted word. If you feel this was a mistake, let staff know.")
                await self.modlog.log_filter("word_blacklist", message)
                await message.delete()
                return

        for url in f["domain_blacklist"]:
            if url in content:
                try:
                    await message.author.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                              f"blacklisted domain. If you feel this was a mistake, let staff know.")
                    await message.author.send(quote(message.content))
                except discord.Forbidden:
                    await message.channel.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                               f"blacklisted domain. If you feel this was a mistake, let staff know.")
                await self.modlog.log_filter("domain_blacklist", message)
                await message.delete()
                return


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Filter(bot))
