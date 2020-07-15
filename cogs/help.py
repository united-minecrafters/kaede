from typing import List, Tuple

import discord
from discord.ext import commands
from disputils import BotEmbedPaginator

import cogs.administration.moderation
from libs.config import config
from libs.utils import pages

NL = "\n"


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _is_allowed_for(self, hs_parsed: Tuple[str, List[str]], ctx: commands.Context):
        if not hs_parsed[1]:
            return True
        for r in hs_parsed[1]:
            if r == "#STAFF" and config()["roles"]["staff"] in [r.id for r in ctx.author.roles]:
                return True
            if r == "#OWNER" and await self.bot.is_owner(ctx.author):
                return True
        return False

    @commands.command()
    async def help(self, ctx: commands.Context, *, cmd_s: str = None):
        if cmd_s:
            cmd: commands.Command
            cmd = self.bot.get_command(cmd_s)
            if not cmd:
                for cmd in self.bot.commands:
                    if cmd_s in cmd.aliases:
                        break
                else:
                    return await ctx.send(embed=discord.Embed(
                        title="Command not found",
                        description=f"Command `{cmd_s}` is not a valid command"
                    ))
            if cmd.name in "ban,sban,softban,kick,skick".split(","):
                return await ctx.send(embed=discord.Embed(
                    title=cmd.name,
                    description=cogs.administration.moderation.MOD_HELP_STR))
            s, roles = parse_help_str(cmd.callback.__doc__)
            return await ctx.send(embed=discord.Embed(
                title=cmd.name,
                description=(roles[0].strip("# ") if roles else "") +
                            f"\n{s.strip(NL)}\n" +  # noqa e131
                            ("Aliases: " + ",".join(f"`{x}`" for x in cmd.aliases) + "\n" if cmd.aliases else ""
                             )))
        cmds: List[commands.Command] = sorted(self.bot.commands, key=lambda x: x.cog_name)
        lst = []
        for i in cmds:
            if i.callback.__doc__:
                s, roles = parse_help_str(i.callback.__doc__)
            else:
                continue
            if await self._is_allowed_for((s, roles), ctx):
                s = s.strip("\n ").splitlines(keepends=False)[0]
                lst.append(f"`{i.name.strip()}`:  " +
                           (roles[0].strip("# ") if roles else "") + "\n" +
                           s + "\n" +
                           ("Aliases: " + ",".join(f"`{x}`" for x in i.aliases) + "\n" if i.aliases else ""))
        embeds = pages(lst, 7, "Help", fmt="%s")
        if config()["roles"]["staff"] in [r.id for r in ctx.author.roles]:
            embeds.append(discord.Embed(title="Help", description=cogs.administration.moderation.MOD_HELP_STR))
        await BotEmbedPaginator(ctx, embeds).run()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Help(bot))


def parse_help_str(hs: str):
    s = ""
    roles = []
    for i in hs.splitlines(keepends=False):
        if not i.strip().startswith("#"):
            s += f"{i}\n"
        else:
            roles.append(i.strip())
    return s, roles
