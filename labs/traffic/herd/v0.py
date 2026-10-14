"""Measure actual coroutine overlap at simultaneous cache expiry."""
import asyncio
import json


class Origin:
    def __init__(self):
        self.calls = self.active = self.peak = 0
        self.release = asyncio.Event()
        self.entered = asyncio.Event()

    async def load(self, key):
        self.calls += 1
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.entered.set()
        try:
            await self.release.wait()
            return "new:" + key
        finally:
            self.active -= 1


async def experiment():
    origin = Origin()
    now = 5.0
    cache = {"hot": ("old", 5.0)}

    async def get(key):
        value, expires = cache[key]
        if now < expires:
            return value
        value = await origin.load(key)
        cache[key] = value, now + 5
        return value

    tasks = [asyncio.create_task(get("hot")) for _ in range(20)]
    await asyncio.sleep(0)
    assert origin.active == origin.peak == origin.calls == 20
    origin.release.set()
    assert await asyncio.gather(*tasks) == ["new:hot"] * 20
    assert origin.active == 0
    return {"requests": 20, "origin_calls": origin.calls, "peak": origin.peak}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(experiment())))
