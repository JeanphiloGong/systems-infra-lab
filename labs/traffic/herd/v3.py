"""Jitter spreads different keys; SWR bounds staleness while one fill runs."""
import asyncio
import json
import random
import sys

from v0 import Origin
from v2 import Flights


class Cache:
    def __init__(self, clock, ttl=5.0, stale_window=5.0):
        if ttl <= 0 or stale_window < 0:
            raise ValueError("invalid freshness policy")
        self.clock, self.ttl, self.stale_window = clock, ttl, stale_window
        self.entries = {}
        self.flights = Flights()

    async def get(self, key, loader):
        entry = self.entries.get(key)
        now = self.clock()
        if entry is not None and now < entry[1]:
            return entry[0]

        async def refresh(item):
            value = await loader(item)
            expires = self.clock() + self.ttl
            self.entries[item] = value, expires, expires + self.stale_window
            return value

        if entry is not None and now < entry[2]:
            self.flights.start(key, refresh)
            return entry[0]
        return await self.flights.get(key, refresh)

    async def close(self):
        await self.flights.close()


async def expiry_wave(jitter):
    # Timestamps are logical slots; loads below are real concurrently waiting tasks.
    rng = random.Random(19)
    expiries = {str(i): 5 + (rng.randrange(4) if jitter else 0) for i in range(20)}
    peak = calls = 0
    flights = Flights()
    for now in range(5, 9):
        keys = [key for key, expires in expiries.items() if expires == now]
        origin = Origin()
        tasks = [asyncio.create_task(flights.get(key, origin.load)) for key in keys]
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert origin.active == len(keys)
        peak = max(peak, origin.peak)
        calls += origin.calls
        origin.release.set()
        assert await asyncio.gather(*tasks) == ["new:" + key for key in keys]
    await flights.close()
    return {"calls": calls, "peak": peak, "expiries": expiries}


async def process_worker():
    origin, flights = Origin(), Flights()
    tasks = [asyncio.create_task(flights.get("hot", origin.load)) for _ in range(20)]
    await origin.entered.wait()
    origin.release.set()
    assert await asyncio.gather(*tasks) == ["new:hot"] * 20
    await flights.close()
    return origin.calls


async def experiment():
    synchronized, jittered = await expiry_wave(False), await expiry_wave(True)
    assert synchronized["calls"] == jittered["calls"] == 20
    assert synchronized["peak"] == 20 and jittered["peak"] < 20
    assert jittered == await expiry_wave(True)

    now = [5.0]
    cache = Cache(lambda: now[0])
    cache.entries["hot"] = "old", 5.0, 10.0
    origin = Origin()
    values = await asyncio.gather(*(cache.get("hot", origin.load) for _ in range(20)))
    await origin.entered.wait()
    assert values == ["old"] * 20 and origin.calls == 1 and origin.active == 1
    now[0] = 10.0
    hard_miss = asyncio.create_task(cache.get("hot", origin.load))
    await asyncio.sleep(0)
    assert not hard_miss.done() and origin.calls == 1
    origin.release.set()
    assert await hard_miss == "new:hot"
    assert cache.entries["hot"] == ("new:hot", 15.0, 20.0)
    await cache.close()

    # Failed refresh must not extend freshness or turn a hard miss into a stale hit.
    now[0] = 5.0
    cache = Cache(lambda: now[0])
    cache.entries["hot"] = "old", 5.0, 10.0
    async def fail(key):
        raise ValueError("refresh unavailable")
    assert await cache.get("hot", fail) == "old"
    task = cache.flights.pending["hot"]
    result = await asyncio.gather(task, return_exceptions=True)
    assert isinstance(result[0], ValueError)
    assert cache.entries["hot"] == ("old", 5.0, 10.0)
    now[0] = 10.0
    try:
        await cache.get("hot", fail)
    except ValueError:
        pass
    else:
        raise AssertionError("hard expiry returned stale on error")
    await cache.close()

    processes = [await asyncio.create_subprocess_exec(
        sys.executable, __file__, "worker", stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE) for _ in range(2)]
    counts = []
    for process in processes:
        stdout, stderr = await asyncio.wait_for(process.communicate(), 5)
        assert process.returncode == 0, stderr.decode()
        counts.append(json.loads(stdout))
    assert counts == [1, 1]
    return {"synchronized": synchronized, "jittered": jittered,
            "swr_stale_responses": len(values), "swr_fills": origin.calls,
            "per_process_fills": counts, "total_cross_process_fills": sum(counts)}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(process_worker() if sys.argv[1:] == ["worker"] else experiment())))
