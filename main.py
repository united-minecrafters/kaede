import logging
import os
import random
import re

import discord
import dotenv
from discord.ext import commands

from libs import utils
from libs.config import config

logging.addLevelName((logging.DEBUG + logging.INFO) // 2, "DEBUG2")

logging.basicConfig(level=logging.getLevelName("DEBUG2"), format="%(asctime)-15s %(message)s",
                    datefmt="%m/%d/%Y %H:%M:%S")
dotenv.load_dotenv()


def get_prefix(bot, message):
    prefixes = config()["prefixes"]
    if not message.guild:
        return '!'
    return commands.when_mentioned_or(*prefixes)(bot, message)


bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')

initial_extensions = ["cogs.search",
                      "cogs.unitedmc",
                      "cogs.administration",
                      "cogs.filters",
                      "cogs.modlog",
                      "cogs.kaede",
                      "cogs.help",
                      "cogs.moderation"]
if __name__ == '__main__':
    for ext in initial_extensions:
        logging.info(f"[BOT] Loading {ext}")
        bot.load_extension(ext)


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Game(name="Hey there!"))
    logging.info(f"[BOT] Kaede online!")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    anti_misfit_regex = r"\bs[kc]re+(?:ch)?\b"
    if re.findall(anti_misfit_regex, re.sub("[*.+?]", "", message.content.lower()), re.MULTILINE).__len__() != 0:
        await message.delete()
        await message.channel.send("No screeching please.", delete_after=30)
    hello_regex = rf"^\s*(?:hi|hiya|hi there|hello|hei|hola|hey),?\s*(?:[Kk]aede|<@!{str(bot.user.id)}>)[!\.]*\s*$"
    if message.content == "<@!" + str(bot.user.id) + ">":
        await message.channel.send(random.choice("I'm alive!,Hm?,Yea? :3,:D,That's me!".split(",")))
    if re.findall(hello_regex, message.content.lower(), re.MULTILINE).__len__() != 0:
        await message.channel.send(random.choice(["Hi, " + message.author.mention + " :3",
                                                  "Hey, " + message.author.display_name,
                                                  "Hi, " + message.author.display_name + " :3",
                                                  "Hey, " + message.author.mention,
                                                  "Hello :D"]))
        return
    if any([s in message.content for s in config()["kaedemojis"]]):
        await message.add_reaction(utils.letter_emoji("M"))
        await message.add_reaction(utils.letter_emoji("E"))
        await message.add_reaction("\u2755")
        await message.add_reaction([e for e in message.guild.emojis if e.id == 715315690105733234][0])
    if message.content == "(╯°□°）╯︵ ┻━┻":
        await message.channel.send("┬─┬ ノ( ゜-゜ノ)")
        if random.randint(1, 10) == 1:
            await message.channel.send(random.choice(config()["no-table-flip"]))
    await bot.process_commands(message)


bot.run(os.getenv("TOKEN"))
