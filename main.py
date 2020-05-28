import logging
import os
import random
import re

import discord
from discord.ext import commands

logging.basicConfig(level=logging.WARN)


def get_prefix(bot, message):
    prefixes = ['!']
    if not message.guild:
        return '!'
    return commands.when_mentioned_or(*prefixes)(bot, message)


bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')

initial_extensions = ["cogs.search", "cogs.unitedmc"]
if __name__ == '__main__':
    for ext in initial_extensions:
        print("= Adding " + ext + " =")
        bot.load_extension(ext)


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Game(name="Hello :)"))
    print("Bot ready!")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.content.lower() == "bruh" and message.author.id == 534419428368973835:
        await message.channel.send("Shut up")
    anti_misfit_regex = r"scr[e3]+ch"
    if re.findall(anti_misfit_regex, message.content.lower(), re.MULTILINE).__len__() != 0:
        await message.delete()
        await message.channel.send("No screeching please.")
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
    if message.content == "(╯°□°）╯︵ ┻━┻":
        await message.channel.send("┬─┬ ノ( ゜-゜ノ)")
        if random.randint(1, 10) == 1:
            await message.channel.send(random.choice([
                "You could have hurt someone ):",
                "Put it back!",
                "Stoppppppppp"
            ]))
    await bot.process_commands(message)


bot.run(os.getenv("KAEDE"))
