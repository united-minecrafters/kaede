from discord.ext import commands, tasks


class UnitedMC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @tasks.loop(seconds=30.0)
    async def update(self):
        pass


def setup(bot):
    bot.add_cog(UnitedMC(bot))
