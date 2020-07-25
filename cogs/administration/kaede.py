import logging
import sys
import traceback
from itertools import cycle
from typing import Optional

import discord
from discord.ext import commands, tasks
from disputils import BotConfirmation, BotEmbedPaginator

from cogs.administration.modlog import ModLog
from libs.config import config, reload_config, save_config
from libs.utils import numbered, pages


class Kaede(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.status: Optional[cycle] = None
        bot.loop.create_task(self._init())
        self.modlog: Optional[ModLog] = None

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound,)
        error = getattr(error, 'original', error)
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"{ctx.author.mention}, you're on cooldown. Try again in {round(error.retry_after, 1)}s")

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"An error occured while executing the command\n{error}")

        else:
            # All other Errors not returned come here. And we can just print the default TraceBack.
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    async def _init(self):
        logging.info("[KAEDE] Waiting for bot")
        await self.bot.wait_until_ready()
        self.status = cycle(config()["statuses"])
        self.status_rotate.start()
        self.modlog = self.bot.get_cog("ModLog")
        await self.bot.change_presence(status=discord.Status.do_not_disturb,
                                       activity=discord.Game(name=self.status.__next__()))
        logging.info("[KAEDE] Ready")

    @tasks.loop(seconds=config()["status_cycle"])
    async def status_rotate(self):
        await self.bot.change_presence(status=discord.Status.do_not_disturb,
                                       activity=discord.Game(name=self.status.__next__()))

    @status_rotate.before_loop
    async def before_status(self):
        await self.bot.change_presence(status=discord.Status.do_not_disturb,
                                       activity=discord.Game(name=self.status.__next__()))

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        if ctx.channel.id not in config()["delete_exceptions"]:
            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass

    @commands.command()
    @commands.is_owner()
    async def logout(self, ctx):
        """
        Log kaede out
        #OWNER
        """
        await ctx.send("Oki")
        await self.bot.logout()

    @commands.command()
    @commands.is_owner()
    async def reloadconfig(self, ctx):
        """
        Reload bot config
        #OWNER
        """
        await ctx.send("Reloading config...")
        try:
            reload_config()
            self.status = cycle(config()["statuses"])
            self.status_rotate.change_interval(seconds=config()["status_cycle"])
            self.status_rotate.restart()
        except Exception as e:  # noqa e722
            await ctx.send("An error occ ured")
            raise e
        else:
            await ctx.send("Config reloaded! :D")

    @commands.command(aliases=["lsst"])
    @commands.is_owner()
    async def liststatus(self, ctx):
        """
        Lists kaede's statuses
        #OWNER
        """
        await BotEmbedPaginator(ctx, pages(numbered(config()["statuses"]), 10, "Statuses")).run()

    @commands.command(aliases=["dlst"])
    @commands.is_owner()
    async def delstatus(self, ctx, n: int):
        """
        Deletes a status
        #OWNER
        """
        if len(config()["statuses"]) == 1:
            await ctx.send("Can't delete only status, do `!resetstatus`")
            return
        if n < 0 or n >= len(config()["statuses"]):
            await ctx.send("Invalid index, do `!liststatus`")
            return
        conf = BotConfirmation(ctx, 0x5555ff)
        await conf.confirm(f'Delete `{config()["statuses"][n]}`?')

        if conf.confirmed:
            try:
                s = config()["statuses"][n]
                del config()["statuses"][n]
                save_config()
                self.status = cycle(config()["statuses"])
                self.status_rotate.restart()
            except Exception as e:  # noqa e722
                await conf.update("An error occurred", color=0xffff00)
            else:
                await conf.update("Deleted!", color=0x55ff55)
                await self.modlog.log_message("Status Modification", f"```diff\n - {s}```", ctx.author)
        else:
            await conf.update("Canceled", color=0xff5555)

    @commands.command(aliases=["adst"])
    @commands.is_owner()
    async def addstatus(self, ctx: commands.Context, *, w: str):
        """
        Adds a status
        #OWNER
        """
        w = w.strip("` ")
        conf = BotConfirmation(ctx, 0x5555ff)
        await conf.confirm(f'Add `{w}`?')

        if conf.confirmed:
            try:
                config()["statuses"].append(w)
                save_config()
                self.status = cycle(config()["statuses"])
                self.status_rotate.restart()
            except Exception as e:  # noqa e722
                await conf.update("An error occurred", color=0xffff00)
            else:
                await conf.update("Added!", color=0x55ff55)
                await self.modlog.log_message("Status Modification", f"```diff\n + {w}```", ctx.author)
        else:
            await conf.update("Canceled", color=0xff5555)

    @commands.command()
    @commands.is_owner()
    async def resetstatus(self, ctx: commands.Context):
        """
        Clear status list
        #OWNER
        """
        conf = BotConfirmation(ctx, 0x5555ff)
        await conf.confirm('Reset status list?')

        if conf.confirmed:
            try:
                config()["statuses"] = ["Hi"]
                save_config()
                self.status = cycle(config()["statuses"])
                self.status_rotate.restart()
            except Exception as e:  # noqa e722
                await conf.update("An error occurred", color=0xffff00)
            else:
                await conf.update("Reset!", color=0x55ff55)
                await self.modlog.log_message("Status Modification", "```# Reset #```", ctx.author)
        else:
            await conf.update("Canceled", color=0xff5555)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Kaede(bot))
