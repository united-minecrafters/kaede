from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Misc(bot))
