import asyncio
from typing import Any, List

import discord
from discord.ext import commands

NBSP = "͔"


def letter_emoji(a: str):
    if a.isascii() and a.isalpha() and len(a) == 1:
        a = a.upper()
    else:
        return None
    return chr(ord(a[0]) + 0x1f1a5)


def quote(st: str):
    return "\n".join(f"> {n}" for n in st.split("\n"))


def cond_trim(st: str): return st if len(st) < 300 else st[:300]


async def trash_reaction(msg: discord.Message, bot: commands.Bot, ctx: commands.Context):
    def check(_reaction: discord.Reaction, _user: discord.User):
        return _user.id == ctx.author.id and _reaction.message.id == msg.id and str(_reaction) == "🗑️"

    await msg.add_reaction("🗑️")
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await msg.clear_reactions()
    else:
        await msg.delete()


def group_list(lst: List[Any], n: int) -> List[List[Any]]:
    return [lst[i * n:(i + 1) * n] for i in range((len(lst) + n - 1) // n)]


def pages(lst: List[Any], n: int, title: str, *, fmt: str = "```%s```", sep: str = "\n") -> List[discord.Embed]:
    l: List[List[str]] = group_list([str(i) for i in lst], n)
    pgs = [sep.join(page) for page in l]
    return [
        discord.Embed(
            title=f"{title} - {i + 1}/{len(pgs)}",
            description=fmt % pg
        ) for i, pg in enumerate(pgs)
    ]


def numbered(lst: List[Any]) -> List[str]:
    return [f"{i} - {a}" for i, a in enumerate(lst)]
