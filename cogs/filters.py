import re

import discord
from discord.ext import commands

from libs.config import config
from libs.utils import quote

url_regex = re.compile(r"(https?://[^\s]+)")


class Filter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content:
            await self.on_message(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        print(1)
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
            print(r)
            if re.match(rf"(?:^|[-\b]){r}([-\b$]|$)", content):
                try:
                    await message.author.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                              f"blacklisted word. If you feel this was a mistake, let staff know.")
                    await message.author.send(quote(message.content))
                except discord.Forbidden:
                    await message.channel.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                               f"blacklisted word. If you feel this was a mistake, let staff know.")
                await message.delete()
                return

        for r in f["token_blacklist"]:
            if re.match(fr"{r}", content):
                try:
                    await message.author.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                              f"blacklisted word. If you feel this was a mistake, let staff know.")
                    await message.author.send(quote(message.content))
                except discord.Forbidden:
                    await message.channel.send(f"Hey, {message.author.mention}, your message was removed because of a "
                                               f"blacklisted word. If you feel this was a mistake, let staff know.")
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
                await message.delete()
                return


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Filter(bot))
