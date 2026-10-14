"""Share a pending task per key; cancellation protection comes in v2."""
import asyncio
import json

from v0 import Origin


class Flights:
    def __init__(self):
        self.pending = {}

    async def get(self, key, loader):
        task = self.pending.get(key)
        if task is None:
            task = asyncio.create_task(loader(key))
            self.pending[key] = task
        try:
            return await task
        finally:
            if task.done() and self.pending.get(key) is task:
                del self.pending[key]


async def experiment():
    origin, flights = Origin(), Flights()
    tasks = [asyncio.create_task(flights.get("hot", origin.load)) for _ in range(20)]
    await origin.entered.wait()
    assert origin.calls == origin.peak == 1
    origin.release.set()
    values = await asyncio.gather(*tasks)
    assert values == ["new:hot"] * 20 and not flights.pending

    # Different keys must not receive the same cached task's result.
    origin = Origin()
    pair = [asyncio.create_task(flights.get(key, origin.load)) for key in ("a", "b")]
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert origin.calls == origin.peak == 2
    origin.release.set()
    assert await asyncio.gather(*pair) == ["new:a", "new:b"]
    return {"same_key_calls": 1, "same_key_results": len(values), "distinct_key_calls": origin.calls}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(experiment())))
