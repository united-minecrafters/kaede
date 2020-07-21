import logging
import random
from typing import List, Tuple, Union

import discord
from discord.ext import commands
from disputils import BotConfirmation, BotEmbedPaginator

from libs.config import config
from libs.utils import pages, trash_send


class CustomReactions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reactions: List[Tuple[str, str]] = []
        logging.info("[CUS] Loading config")
        self._load_cr()
        logging.info(f"[CUS] Found {len(self.reactions)} custom reactions")

    def _save_cr(self):
        with open("configs/custom_reactions.csv", "w") as fp:
            fp.writelines([f"{e[0]}\t{e[1]}\n" for e in self.reactions])

    def _load_cr(self):
        self.reactions = []
        with open("configs/custom_reactions.csv") as fp:
            for i in fp.readlines():
                entry = i.strip().split("\t")
                self.reactions.append((entry[0], entry[1]))

    @commands.has_role(config()["roles"]["staff"])
    @commands.command(aliases=["acr"])
    async def addcustomreaction(self, ctx: commands.Context, trigger: str, *, response: str):
        """
        Adds a custom reaction
        !acr trigger response
        !placeholders
        #STAFF
        """
        self.reactions.append((trigger, response))
        await ctx.send(f"Added {trigger}: {response}")
        self._save_cr()

    @commands.is_owner()
    @commands.command(aliases=["rcr"])
    async def reloadcustomreactions(self, ctx: commands.Context):
        """
        Reloads custom reactions
        #OWNER
        """
        self._load_cr()

    def _search(self, trigger: str = None):
        cs_list = []
        for n, r in enumerate(self.reactions):
            if trigger == r[0] or not trigger:
                cs_list.append(f"{n + 1}: **{r[0]}** - {r[1]}")
        return cs_list

    @commands.has_role(config()["roles"]["staff"])
    @commands.command(aliases=["lcr"])
    async def listcustomreactions(self, ctx: commands.Context, trigger: str = None):
        """
        lists custom reactions, optionally by trigger
        #STAFF
        """
        cs_list: List[str] = self._search(trigger)
        if len(cs_list) == 0:
            if not trigger:
                return await ctx.send("No reactions")
            return await ctx.send(f"No reactions found for trigger `{trigger}`")
        await BotEmbedPaginator(ctx, pages(cs_list, 10, "Reactions", fmt="%s")).run()

    @commands.has_role(config()["roles"]["staff"])
    @commands.command(aliases=["dcr"])
    async def delcustomreaction(self, ctx: commands.Context, trigger: Union[int, str]):
        """
        Deletes a custom reaction by index or trigger
        """

        async def del_confirm(t: int):
            conf = BotConfirmation(ctx, 0x0000aa)
            await conf.confirm(f"Delete {t} (**{self.reactions[t - 1][0]}**: {self.reactions[t - 1][1]})?")
            if conf.confirmed:
                await conf.update(f"{t} (**{self.reactions[t - 1][0]}**: {self.reactions[t - 1][1]}) deleted",
                                  color=0x00aa00)
                del self.reactions[t - 1]
                self._save_cr()
            else:
                await conf.update("Cancelled", color=0xaa0000)

        if isinstance(trigger, int):
            if 0 <= trigger - 1 < len(self.reactions):
                return await del_confirm(trigger)
            else:
                return await ctx.send("Invalid reaction, do `!lcr`")
        reactions = self._search(trigger)
        if len(reactions) == 0:
            return await ctx.send("Invalid reaction, do `!lcr`")
        if len(reactions) == 1:
            return await del_confirm(int(reactions[0].split(":")[0]))
        await ctx.send(f"There's more than one match. Do `!lcr {trigger}` to find the number to delete.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        reactions = self._search(message.content)
        if len(reactions) == 0:
            return
        sel = random.choice(reactions)
        num = int(sel.split(":")[0])
        await message.channel.send(self.reactions[num - 1][1]
                                   .replace("%user.mention%", message.author.mention)
                                   .replace("%user%", str(message.author))
                                   .replace("%guild%", message.guild.name))

    @commands.command()
    async def placeholders(self, ctx: commands.Context):
        await trash_send(discord.Embed(
            title="Placeholders",
            description="`%user.mention%` - mentions a user\n"
                        "`%user%` - username#0000\n"
                        "`%guild%` - guild name"
        ), self.bot, ctx)


def setup(bot):
    bot.add_cog(CustomReactions(bot))
