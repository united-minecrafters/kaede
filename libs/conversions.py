from dataclasses import dataclass


class TimeDelta:
    def __init__(self, *, seconds: int = 0, minutes: int = 0, hours: int = 0):
        self.seconds = seconds
        self.minutes = minutes
        self.hours = hours

    def total_seconds(self):
        return self.hours * 3600 + self.minutes * 60 + self.seconds

    @classmethod
    def from_seconds(cls, num: int):
        return TimeDelta(seconds=num % 60,
                         minutes=(num % 3600) // 60,
                         hours=num // 3600)

    @classmethod
    def parse(cls, time: str):
        if time.endswith("s"):
            return TimeDelta(seconds=int(time[:-1]))
        if time.endswith("m"):
            return TimeDelta(minutes=int(time[:-1]))
        if time.endswith("h"):
            return TimeDelta(hours=int(time[:-1]))
        num = int(time)
        return TimeDelta(seconds=num % 60,
                         minutes=(num % 3600) // 60,
                         hours=num // 3600)

    def __str__(self):
        return f"**{self.hours}**h**{self.minutes}**m**{self.seconds}**s"



def str_to_seconds(t: str) -> int:
    return 0


def seconds_to_str(seconds: int) -> str:
    return f"{seconds}s"



