import ast

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

    def insert_returns(self, body):
        # insert return stmt if the last expression is a expression statement
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])

        # for if statements, we insert returns into the body and the orelse
        if isinstance(body[-1], ast.If):
            self.insert_returns(body[-1].body)
            self.insert_returns(body[-1].orelse)

        # for with blocks, again we insert returns into the body
        if isinstance(body[-1], ast.With):
            self.insert_returns(body[-1].body)

    @commands.is_owner()
    @commands.command()
    async def eval(self, ctx, *, cmd):
        if ctx.author.id != 267499094090579970:
            return
        """Evaluates input.
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
          - `bot`: the bot instance
          - `discord`: the discord module
          - `commands`: the discord.ext.commands module
          - `ctx`: the invokation context
          - `__import__`: the builtin `__import__` function
        Such that `>eval 1 + 1` gives `2` as the result.
        The following invokation will cause the bot to send the text '9'
        to the channel of invokation and return '3' as the result of evaluating
        >eval ```
        a = 1 + 2
        b = a * 2
        await ctx.send(a + b)
        a
        ```
        https://gist.github.com/nitros12/2c3c265813121492655bc95aa54da6b9
        """
        fn_name = "_eval_expr"

        cmd = cmd.strip("` ")

        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        self.insert_returns(body)

        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__
        }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = (await eval(f"{fn_name}()", env))
        await ctx.send(result)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Administration(bot))
