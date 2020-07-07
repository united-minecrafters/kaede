import datetime
import logging
from dataclasses import dataclass
from typing import List, Optional

import aiosqlite
from discord.ext import commands


@dataclass
class Record:
    user: int
    staff: int
    reason: str
    id: str = None
    timestamp: float = None
    cleared: bool = False
    typ: str = ""


class Punishments(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conn: Optional[aiosqlite.Connection] = None
        bot.loop.create_task(self._init())

    async def _init(self):
        logging.info("[PUNISHMENTS] Waiting for bot")
        await self.bot.wait_until_ready()
        logging.info("[PUNISHMENTS] Connecting to database")
        self.conn = await aiosqlite.connect("punishments.db")
        logging.info("[PUNISHMENTS] Ready")

    async def insert_warn_record(self, rec: Record):
        await self.conn.execute("insert into warns(user, staff, reason, timestamp) values (?,?,?,?)",
                                (rec.user, rec.staff, rec.reason, datetime.datetime.utcnow().timestamp()))
        await self.conn.commit()

    async def get_warn_records(self, user_id: int) -> Optional[List[Record]]:
        results = await (await self.conn.execute("select * from warns where user=?", (user_id,))).fetchall()
        if not results:
            return None
        return [Record(staff=r[2], user=r[1], id=r[0], timestamp=r[3],
                       cleared=r[5], reason=r[4], typ="W") for r in results]

    async def insert_ban_record(self, rec: Record):
        await self.conn.execute("insert into bans(user, staff, reason, timestamp) values (?,?,?,?)",
                                (rec.user, rec.staff, rec.reason, datetime.datetime.utcnow().timestamp()))
        await self.conn.commit()

    async def get_ban_records(self, user_id: int) -> Optional[List[Record]]:
        results = await (await self.conn.execute("select * from bans where banned_user=?", (user_id,))).fetchall()
        if not results:
            return None
        return [Record(staff=r[2], user=r[1], id=r[0], timestamp=r[3],
                       cleared=r[5], reason=r[4], typ="B") for r in results]


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Punishments(bot))
