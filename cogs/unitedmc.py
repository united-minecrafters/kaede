import asyncio
import concurrent.futures
import json
import logging
import platform
import re
import socket
import subprocess
from typing import Dict

import discord
from discord.ext import commands, tasks
import mcstatus

from libs.mcrcon import MinecraftClient
from libs.utils import mc_to_md


async def ping(url: str):
    ping_var = "-n" if platform.system() == "Windows" else "-c"

    def pshell(url: str):
        return str(subprocess.check_output(["ping", url, ping_var, "2"]), "utf-8")

    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            s = await asyncio.get_event_loop().run_in_executor(pool, pshell, url)
        print(s)
        try:
            if platform.system() != "Windows":
                ar = s.strip("\n\r").split("\r\n")[-1].split(" ")[-2].split("/")
                return f"{ar[0]} ms", f"{ar[2]} ms"
            else:
                ar = s.strip("\n\r").split("\r\n")[-1].split(" ")
                return ar[-7].strip(","), ar[-4].strip(",")
        except Exception as e:
            print(e)
    except Exception as e:
        print(e)
        print(type(e))
        return "ERR", "ERR"

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
                              description="Do `!server server_name` to check a server")
        for name, server in self.servers.items():
            embed.add_field(name=name,
                            value=f":envelope: **Address**: {server['address']}\n"
                                  f":envelope: **IP:Port**: {server['ip']}:{server['port']}\n"
                                  f":gear: **Software**: {server['version']}\n" +
                                  (
                                      f":white_check_mark: **Requirements**: {server['requirements']}\n" if
                                      "requirements" in server else "") +
                                  (":lock: Whitelisted" if "whitelist" in server and server[
                                      "whitelist"] else ":earth_americas: Public") +
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
                description=f"An error has occurred. Is the server online?",
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
            try:
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
            except ConnectionRefusedError:
                await ctx.send("The connection was refused - is the server online?")
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
        await ctx.send("Reloading server config...")
        self._load_server_list()
        await ctx.send("Server config reloaded! :D")

    def _load_server_list(self):
        logging.info("[SVR] Loading server config...")
        with open("servers.json") as js:
            self.servers = json.load(js)
        logging.info("[SVR] Server config loaded! :D")

    @commands.command(name="server")
    async def _server(self, ctx: commands.Context, server: str):
        if server not in self.servers.keys():
            await ctx.send("Invalid server ):")
            return
        svr: Dict = self.servers[server]
        bedrock = ("bedrock" in svr["version"].lower())
        if bedrock:
            url = f'{svr["ip"]}:{svr["port"]}'
            try:
                if len(url.split(":")) == 2:
                    port = int(url.split(":")[1])
                    url = url.split(":")[0]
                else:
                    port = 19132
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setblocking(False)
                sock.settimeout(10)
                sock.sendto(bytearray.fromhex(
                    "0100000000003c6d0d00ffff00fefefefefdfdfdfd12345678"), (url, port))
                data, addr = sock.recvfrom(255)
                status = data[35::].decode("ISO-8859-1").split(";")
                e = discord.Embed()
                e.title = url
                e.description = re.sub("[§Â].", "", status[1])
                e.add_field(name="Players", value=status[4] + "/" + status[5])
                e.add_field(name="Version", value=status[3])
                e.add_field(name="Protocol", value="v" + status[2])
                e.add_field(name="World Name", value=re.sub("§.", "", status[7]))
                e.add_field(name="Default Gamemode", value=status[8])
                await ctx.send(embed=e)
            except socket.timeout as t:
                await ctx.send("Looks like the ping I made to " + url + ":" + str(port) + " timed out. "
                                                                "port.")
            except socket.gaierror as e:
                await ctx.send("I can't figure out how to reach that URL. ): Double check that it's correct.")
                return
            except Exception as e:
                await ctx.send("An unknown error happened"
                               " while I was pinging the server.")
                print(e)
        else:
            server = mcstatus.MinecraftServer.lookup(f'{svr["ip"]}:{svr["port"]}')
            status = server.status()
            e = discord.Embed()
            e.title = f'{svr["ip"]}:{svr["port"]}'
            e.description = mc_to_md(status.description)
            e.add_field(name="Players", value=str(status.players.online) + "/" + str(status.players.max))
            e.add_field(name="Ping", value=str(status.latency))
            e.add_field(name="Version", value=status.version.name)
            e.add_field(name="Protocol", value="v" + str(status.version.protocol))
            await ctx.send(embed=e)

def setup(bot):
    bot.add_cog(UnitedMC(bot))
