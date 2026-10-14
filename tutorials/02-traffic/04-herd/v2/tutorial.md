# F04 v2：取消一个等待者，不取消所有人的结果

用户关闭页面时取消的是自己的等待，不能取消其他用户共享的加载。另一方面，如果源永远不回应，共享任务也不能永远留在 pending。把请求等待期限和源加载期限分成两层，分别验证它们的结果。

## 1. 从上一版的缺口到本版规则

start 创建受 fill_timeout 限制的任务。get 用 shield 阻止调用者取消传播到它，再用 asyncio.timeout(wait_timeout) 限制这一个等待者。fill 的超时在内部取消异步加载，并向所有等待者返回 TimeoutError。done callback 在任务完成时清理映射；即使所有人离开，也读取异常，避免未观察异常警告。读取 exception 不会吞掉仍在 await 的人的异常。

## 2. 完整 checkpoint

实验先取消首个请求，再让一个等待者超时，最后放行源，确认另一个请求成功且只回源一次。之后分别让源抛错、源超时、填充 Task 被直接取消，检查所有等待者获得同类结果、pending 清空以及新请求可重新填充。close 取消并回收剩余任务；正常服务退出应执行它。

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

## 3. 运行与冻结

```bash
uv run python labs/traffic/herd/v2.py
uv run pytest tests/traffic/herd -q -k "[2]"
```

验收结果：取消/超时不破坏其他等待者；源失败扇出；源超时与取消清理；后续请求重试成功。 脚本中的断言会检查这些语义，pytest 还会逐字核对正文源码，写入临时目录后以独立解释器运行。本实验用 Event 和调度让出点安排交错，不依赖猜测任务已开始的固定长 sleep。

失败与等待者隔离现在可解释。下一版比较不同键随机过期和同键 SWR；这两种策略解决的是不同压力。

所有计数是实验中的实际加载进入次数；TTL/过期时隙是逻辑时间。asyncio 的取消是协作式的，不会抢占阻塞的同步调用。没有多线程安全、跨进程共享缓存、无限重试或生产延迟保证。

