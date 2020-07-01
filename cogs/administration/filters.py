import logging
import re
from typing import Optional

import discord
from discord.ext import commands
from disputils import BotConfirmation, BotEmbedPaginator

import cogs.administration.modlog
from libs.config import config, save_config
from libs.utils import numbered, pages, quote

url_regex = re.compile(r"(https?://[^\s]+)")


class Filter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modlog: Optional[cogs.administration.modlog.ModLog] = None
        bot.loop.create_task(self._init())

    async def _init(self):
        logging.info("[FILTER] Waiting for bot")
        await self.bot.wait_until_ready()
        self.modlog = self.bot.get_cog("ModLog")
        logging.info("[FILTER] Ready")

    @commands.command(aliases=["lfw"])
    @commands.has_role(config()["roles"]["staff"])
    async def listfilteredwords(self, ctx: commands.Context):
        """
        Lists the filtered words
        #STAFF
        """
        await BotEmbedPaginator(ctx, pages(numbered(config()["filters"]["word_blacklist"]), 10, "Filtered Words")).run()

    @commands.command(aliases=["lft"])
    @commands.has_role(config()["roles"]["staff"])
    async def listfilteredtoken(self, ctx: commands.Context):
        """
        Lists filtered tokens
        #STAFF
        """
        await BotEmbedPaginator(ctx,
                                pages(numbered(config()["filters"]["token_blacklist"]), 10, "Filtered Tokens")).run()

    @commands.command(aliases=["dfw"])
    @commands.has_role(config()["roles"]["staff"])
    async def delfilteredword(self, ctx: commands.Context, n: int):
        """
        Delete a filtered word
        #STAFF
        """
        if n < 0 or n >= len(config()["filters"]["word_blacklist"]):
            await ctx.send("Invalid number - do `!lfw` to view")
        conf = BotConfirmation(ctx, 0x5555ff)
        await conf.confirm(f'Delete `{config()["filters"]["word_blacklist"][n]}`?')

        if conf.confirmed:
            try:
                s = config()["filters"]["word_blacklist"][n]
                del config()["filters"]["word_blacklist"][n]
                save_config()
            except Exception as e:  # noqa e722
                await conf.update("An error occurred", color=0xffff00)
            else:
                await conf.update("Deleted!", color=0x55ff55)
                await self.modlog.log_message(ctx.author, "Filter Word Modification", f"```diff\n - {s}```")
        else:
            await conf.update("Canceled", color=0xff5555)

    @commands.command(aliases=["dft"])
    @commands.has_role(config()["roles"]["staff"])
    async def delfilteredtoken(self, ctx: commands.Context, n: int):
        """
        Delete a filtered token
        #STAFF
        """
        if n < 0 or n >= len(config()["filters"]["token_blacklist"]):
            await ctx.send("Invalid number - do `!lfw` to view")
        conf = BotConfirmation(ctx, 0x5555ff)
        await conf.confirm(f'Delete `{config()["filters"]["token_blacklist"][n]}`?')

        if conf.confirmed:
            try:
                s = config()["filters"]["token_blacklist"][n]
                del config()["filters"]["token_blacklist"][n]
                save_config()
            except Exception as e:  # noqa e722
                await conf.update("An error occurred", color=0xffff00)
            else:
                await conf.update("Deleted!", color=0x55ff55)
                await self.modlog.log_message(ctx.author, "Filter Token Modification", f"```diff\n - {s}```")
        else:
            await conf.update("Canceled", color=0xff5555)

    @commands.command(aliases=["ft", "aft"])
    @commands.has_role(config()["roles"]["staff"])
    async def addfilteredtoken(self, ctx: commands.Context, *, w: str):
        """
        Add a filtered token
        #STAFF
        """
        w = w.strip("` ")
        conf = BotConfirmation(ctx, 0x5555ff)
        await conf.confirm(f'Add `{w}`?')

        if conf.confirmed:
            try:
                config()["filters"]["token_blacklist"].append(w)
                save_config()
            except Exception as e:  # noqa e722
                await conf.update("An error occurred", color=0xffff00)
            else:
                await conf.update("Added!", color=0x55ff55)
                await self.modlog.log_message(ctx.author, "Filter Token Modification", f"```diff\n + {w}```")
        else:
            await conf.update("Canceled", color=0xff5555)

    @commands.command(aliases=["fw", "afw"])
    @commands.has_role(config()["roles"]["staff"])
    async def addfilteredword(self, ctx: commands.Context, *, w: str):
        """
        Add a filtered word
        #STAFF
        """
        w = w.strip("` ")
        conf = BotConfirmation(ctx, 0x5555ff)
        await conf.confirm(f'Add `{w}`?')

        if conf.confirmed:
            try:
                config()["filters"]["word_blacklist"].append(w)
                save_config()
            except Exception as e:  # noqa e722
                await conf.update("An error occurred", color=0xffff00)
            else:
                await conf.update("Added!", color=0x55ff55)
                await self.modlog.log_message(ctx.author, "Filter Word Modification", f"```diff\n + {w}```")
        else:
            await conf.update("Canceled", color=0xff5555)

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
        f = config()["filters"]
        content = message.content.lower()

        for r in f["role_whitelist"]:
            if r in [a.id for a in message.author.roles[1:]]:
                return

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
