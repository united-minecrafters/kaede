import discord
from discord.ext import commands


class Kaede(commands.Cog):
    def __init__(self, bot: commands.Bot):
        print("")
        self.bot = bot
        print("")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Kaede(bot))
