import os
from typing import Tuple, Optional
import json
import aiohttp
from discord.ext import commands


class Hypixel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.key: str = os.getenv("HYPIXEL")

    async def _lookup(self, username) -> Tuple[Optional[str], Optional[str]]:  # noqa
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"https://api.mojang.com/users/profiles/minecraft/{username}") as resp:
                if resp.status != 200:
                    return None, None
                js = await resp.json()
                if "error" in js:
                    return None, None
                return js["name"], js["id"]

    @commands.command()
    async def uuid(self, ctx: commands.Context, username: str):
        name, uuid = await self._lookup(username)
        if not name:
            return await ctx.send("Invalid username")
        await ctx.send(f"UUID of `{name}` is `{uuid}`")


def setup(bot):
    bot.add_cog(Hypixel(bot))
