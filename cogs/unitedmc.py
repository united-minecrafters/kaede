import asyncio
import json
import logging
from typing import Dict

import discord
from discord.ext import commands, tasks

from libs.mcrcon import MinecraftClient


class UnitedMC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info(f"[UNITED] Loading server list")
        self.servers = {}
        self._load_server_list()

    @tasks.loop(seconds=30.0)
    async def update(self):
        pass

    @commands.command()
    async def servers(self, ctx: commands.Context):
        """
        Lists the servers
        """
        embed = discord.Embed(title="United Minecrafters Servers",
                              description="Do `!server servername` to check a server")
        for name, server in self.servers.items():
            embed.add_field(name=name,
                            value=f":envelope: **Address**: {server['address']}\n"
                                  f":envelope: **IP:Port**: {server['ip']}:{server['port']}\n"
                                  f":gear: **Software**: {server['version']}\n" +
                                  (f":white_check_mark: **Requirements**: {server['requirements']}\n" if "requirements" in server else "") +
                                  (":lock: Whitelisted" if "whitelist" in server and server["whitelist"] else ":earth_americas: Public") +
                                  (", :desktop: RCON" if "rcon" in server.keys() else "") +
                                  f", {server.get('mode', 'Survival').title()}",
                            inline=False
                            )
        await ctx.send(embed=embed)

    @commands.command()
    async def list(self, ctx: commands.Context, server: str):
        """
        Lists the users on a server
        """
        if server not in self.servers.keys():
            await ctx.send("Invalid server ): Do !servers to see a list of servers")
            return
        svr: Dict = self.servers[server]
        if "rcon" not in svr.keys():
            await ctx.send("Remote control not enabled for this server")
            return
        try:
            async with MinecraftClient(svr["ip"], svr["rcon"], svr["password"]) as mc:
                await ctx.send(embed=discord.Embed(
                    title=server,
                    description=await mc.send("list"),
                    color=discord.Colour.green()),
                )
        except ConnectionRefusedError:
            await ctx.send(embed=discord.Embed(
                title=f"{server} - Error",
                description=f"An error has occured. Is the server online?",
                color=discord.Colour.red())
                           .set_footer(text="ConnectionRefusedError"),
                           )

    @commands.command()
    async def send(self, ctx: commands.Context, server: str, *, cmd: str):
        """
        Sends an RCON command to a server - you must be opped
        #STAFF
        """
        if server not in self.servers.keys():
            await ctx.send("Invalid server ):")
            return
        svr: Dict = self.servers[server]
        if "rcon" not in svr.keys():
            await ctx.send("No RCon port set for this server")
            return
        if ctx.author.id not in svr["ops"]:
            await ctx.send("You aren't listed as an op on this server")
            return
        if cmd == "stop":
            async with MinecraftClient(svr["ip"], svr["rcon"], svr["password"]) as mc:
                msg: discord.Message = await ctx.send("[KAEDE] Sending /stop")
                await msg.edit(content=msg.content + "\n[SERVER] " + await mc.send(cmd))
                await msg.edit(content=msg.content + "\n[KAEDE] Waiting for server to come back online...")
                content = msg.content
                cnt = 1
                await asyncio.sleep(2)
                while True:
                    await msg.edit(content=content + f"\n[PING] {cnt}")
                    try:
                        async with MinecraftClient(svr["ip"], svr["rcon"], svr["password"]) as test:
                            output = await test.send("list")
                        if not output:
                            cnt += 1
                            continue
                        break
                    except ConnectionRefusedError:
                        cnt += 1
                await msg.edit(content=content + f"\nOnline!\n[SERVER] {output}")
                return
        async with MinecraftClient(svr["ip"], svr["rcon"], svr["password"]) as mc:
            output = await mc.send(cmd)
            if len(output) > 900:
                output = f"== Output too long ==\n```{output[:900]}```== Output Truncated =="
            else:
                output = f"```{output}```"
            await ctx.send(embed=discord.Embed(title=cmd,
                                               description=output))

    @commands.command()
    @commands.is_owner()
    async def reloadservers(self, ctx: commands.Context):
        """
        Reloads the server list
        #OWNER
        """
        await ctx.send("Reoading server config...")
        self._load_server_list()
        await ctx.send("Server config reloaded! :D")

    def _load_server_list(self):
        logging.info("[SVR] Loading server config...")
        with open("servers.json") as js:
            self.servers = json.load(js)
        logging.info("Server config loaded! :D")


def setup(bot):
    bot.add_cog(UnitedMC(bot))
