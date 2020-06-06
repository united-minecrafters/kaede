import discord
from discord.ext import commands


class Administration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def color(self, ctx: commands.Context, clr: discord.Color):
        if 608403610551713880 not in [r.id for r in ctx.author.roles]:
            await ctx.send("Um. *no you can't do that*")
            return
        m: discord.Member = ctx.author
        await m.top_role.edit(color=clr)
        await ctx.send(":)")

    @color.error
    async def color_err(self, ctx, error2):
        await ctx.send("heh...*nope*")

    @commands.command()
    async def role(self, ctx: commands.Context, *, role: str):
        if 608403610551713880 not in [r.id for r in ctx.author.roles]:
            await ctx.send("Um. *no you can't do that*")
            return
        if len(role) > 32:
            await ctx.send("You...want to name it...*what*?")
            return
        m: discord.Member = ctx.author
        await m.top_role.edit(name=role)
        await ctx.send(":)")

    @role.error
    async def role_err(self, ctx, error2):
        await ctx.send("heh...*nope*")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Administration(bot))
