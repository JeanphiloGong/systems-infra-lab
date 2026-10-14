# F04 v3：随机过期与 SWR，各自改变什么

single-flight 只能合并相同键。20 个不同键在同一时刻过期，仍会有 20 个填充者。随机过期把不同键的过期时刻分散；stale-while-revalidate 则允许热点键在有限窗口内立即返回旧值，同时后台更新。两者不能互相替代。

## 1. 从上一版的缺口到本版规则

expiry_wave 用固定种子把 20 个键安排到 5..8 四个逻辑时隙。每个时隙启动真实 Task 并阻塞源，测 active/peak 后才放行，因此峰值来自执行。逻辑时钟让调度可重放；不是随机网络负载或墙钟性能保证。Cache 沿用 v2 的 Flights，条目包含值、fresh 截止与 stale 截止。fresh 时直接返回；stale 时启动/复用后台刷新并立即返回旧值；硬到期时等待刷新，绝不继续悄悄返回旧值。

## 2. 完整 checkpoint

20 个同键 stale 请求立即拿到 old，而源仍被 Event 阻塞且只有一次加载。在精确时刻 10 的请求必须等待，放行后拿到 new，刷新时刻重设 fresh/stale 边界。另一个场景使后台刷新失败，证明不会延长旧值有效期，硬到期后错误向调用者传播。两个真实子进程各自运行 20 请求合并实验，最终 [1,1] 表明本地映射没有跨进程去重。这里每个进程的数据源是独立计数探针，不声称已经建立共享分布式缓存。

本版只使用 Python 3.12 标准库。以下注释给出各文件的路径；依赖也完整打印，独立回放不从工作树补取模块。v0 中的 Origin 是测量探针，复用它不会为被测实现提供合并行为。

<!-- checkpoint: labs/traffic/herd/v0.py -->

```python
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
```

<!-- checkpoint: labs/traffic/herd/v2.py -->

```python
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
```

<!-- checkpoint: labs/traffic/herd/v3.py -->

```python
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
```

## 3. 运行与冻结

```bash
uv run python labs/traffic/herd/v3.py
uv run pytest tests/traffic/herd -q -k "[3]"
```

验收结果：随机过期峰值低于同步过期且同种子可重放；SWR 立即旧读与一次后台加载；硬过期等待；失败不续期；两个进程各一次。 脚本中的断言会检查这些语义，pytest 还会逐字核对正文源码，写入临时目录后以独立解释器运行。本实验用 Event 和调度让出点安排交错，不依赖猜测任务已开始的固定长 sleep。

可以在另一个专题加入带 fencing 的分布式租约，但那会引入持久化与故障恢复。当前边界是单事件循环、协作式可取消异步源；忽略取消或阻塞事件循环的加载器不能获得这里的期限保证。

所有计数是实验中的实际加载进入次数；TTL/过期时隙是逻辑时间。asyncio 的取消是协作式的，不会抢占阻塞的同步调用。没有多线程安全、跨进程共享缓存、无限重试或生产延迟保证。

