import datetime
from typing import Any, Dict, Hashable, List

from discord.ext import commands, tasks


class Cache(commands.Cog):
    def __init__(self, sz=1024, ttl=600):
        self.items: Dict[Hashable, Any] = {}
        self.timestamps: Dict[Hashable, int] = {}
        self.cache_loop.start()

    def get(self, key: Hashable):
        return self.items.get(key, None)

    def put(self, key: Hashable, value: Any):
        self.items[key] = value
        self.timestamps[key] = int(datetime.datetime.utcnow().timestamp())

    @tasks.loop(seconds=60)
    def cache_loop(self):
        pass

    def _find_oldest(self) -> Hashable:
        min_ts = None
        min_key = None
        for k, v in self.timestamps.items():
            if not min_ts:
                min_ts = v
            if v < min_ts:
                min_ts = v
                min_key = k
        return min_key

    def _find_before(self, ts: int) -> List[Hashable]:
        keys = []
        for k, v in self.timestamps.items():
            if v < ts:
                keys.append(k)
        return keys
