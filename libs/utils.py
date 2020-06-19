import asyncio

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
