import discord
from discord.ext import commands


class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tasks = []



def setup(bot: commands.Bot) -> None:
    bot.add_cog(Scheduler(bot))
