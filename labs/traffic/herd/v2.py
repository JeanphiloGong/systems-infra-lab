"""Cancellation-isolated fills with separate waiter and origin deadlines."""
import asyncio
import json

from v0 import Origin


class Flights:
    def __init__(self, fill_timeout=1.0):
        if fill_timeout <= 0:
            raise ValueError("positive fill timeout required")
        self.fill_timeout = fill_timeout
        self.pending = {}

    def start(self, key, loader):
        task = self.pending.get(key)
        if task is not None:
            return task

        async def fill():
            async with asyncio.timeout(self.fill_timeout):
                return await loader(key)

        task = asyncio.create_task(fill())
        self.pending[key] = task

        def finished(done):
            if self.pending.get(key) is done:
                del self.pending[key]
            # An abandoned or SWR fill still has its exception observed.
            if not done.cancelled():
                done.exception()

        task.add_done_callback(finished)
        return task

    async def get(self, key, loader, wait_timeout=None):
        task = self.start(key, loader)
        async with asyncio.timeout(wait_timeout):
            return await asyncio.shield(task)

    async def close(self):
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def experiment():
    origin, flights = Origin(), Flights()
    owner = asyncio.create_task(flights.get("hot", origin.load))
    peer = asyncio.create_task(flights.get("hot", origin.load))
    await origin.entered.wait()
    owner.cancel()
    assert isinstance((await asyncio.gather(owner, return_exceptions=True))[0], asyncio.CancelledError)
    try:
        await flights.get("hot", origin.load, wait_timeout=0.01)
    except TimeoutError:
        pass
    else:
        raise AssertionError("waiter did not time out")
    assert not peer.done() and origin.calls == 1
    origin.release.set()
    assert await peer == "new:hot"
    await flights.close()

    started, release = asyncio.Event(), asyncio.Event()
    failed_calls = 0

    async def fail(key):
        nonlocal failed_calls
        failed_calls += 1
        started.set()
        await release.wait()
        raise ValueError("origin failed")

    flights = Flights()
    waiters = [asyncio.create_task(flights.get("hot", fail)) for _ in range(3)]
    await started.wait()
    release.set()
    outcomes = await asyncio.gather(*waiters, return_exceptions=True)
    assert all(isinstance(value, ValueError) for value in outcomes)
    assert failed_calls == 1 and not flights.pending

    stalled = Origin()
    bounded = Flights(fill_timeout=0.02)
    outcomes = await asyncio.gather(*(bounded.get("hot", stalled.load) for _ in range(3)), return_exceptions=True)
    assert all(isinstance(value, TimeoutError) for value in outcomes)
    assert stalled.calls == 1 and stalled.active == 0 and not bounded.pending

    cancelled = Origin()
    waiters = [asyncio.create_task(flights.get("hot", cancelled.load)) for _ in range(2)]
    await cancelled.entered.wait()
    flights.pending["hot"].cancel()
    outcomes = await asyncio.gather(*waiters, return_exceptions=True)
    assert all(isinstance(value, asyncio.CancelledError) for value in outcomes)
    assert not flights.pending and cancelled.active == 0
    cancelled.release.set()
    assert await flights.get("hot", cancelled.load) == "new:hot"
    assert cancelled.calls == 2
    await flights.close()
    return {"cancelled_waiter_isolated": True, "timed_out_waiter_isolated": True,
            "failure_fanout": failed_calls, "fill_timeout_calls": stalled.calls,
            "cancelled_fill_retry_calls": cancelled.calls}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(experiment())))
