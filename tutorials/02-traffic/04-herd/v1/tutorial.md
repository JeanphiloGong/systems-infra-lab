# F04 v1：同一个键，只让一个填充者回源

v0 的 20 个调用读取同一份数据。让第一个请求创建加载 Task，并在等待前把它放入 pending[key]。后来的同键请求看到已有 Task，就等待同一个结果；不同键仍应独立加载。这个版本只解决正常完成的路径。

## 1. 从上一版的缺口到本版规则

Flights 只拥有在途任务，不保存 TTL 缓存值。单事件循环内，从查 pending 到赋值之间没有 await，因此不会有另一个协程插入这段操作。这里不需要线程锁，也不支持跨线程调用。完成后删除登记时比较任务身份，防止旧任务清理误删新的填充。

## 2. 完整 checkpoint

实验沿用 v0 的阻塞数据源，20 个真实等待者只让 Origin 进入一次。放行后检查 20 个结果完全一致，再让 a/b 两个键一起加载，验证结果与任务没有串键。这里直接 await 共享 Task 有一个故意保留的缺陷：取消一个等待者可能沿 await 链取消所有人的填充。

本版只使用 Python 3.12 标准库。以下注释给出各文件的路径；依赖也完整打印，独立回放不从工作树补取模块。v0 中的 Origin 是测量探针，复用它不会为被测实现提供合并行为。

将下面的完整代码保存为 `labs/traffic/herd/v0.py`；文件已存在时，以本版内容替换该文件。

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

将下面的完整代码保存为 `labs/traffic/herd/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/traffic/herd/v1.py -->

```python
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
```

## 3. 运行与冻结

```bash
uv run python labs/traffic/herd/v1.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/traffic/herd -q -k "[1]"
```

</details>

验收结果：20 个同键等待者一次回源；两个不同键两次回源；完成后 pending 为空。 脚本中的断言会检查这些语义，pytest 还会逐字核对正文源码，写入临时目录后以独立解释器运行。本实验用 Event 和调度让出点安排交错，不依赖猜测任务已开始的固定长 sleep。

正常请求合并已经成立。下一版会取消首个请求、让另一个请求超时，并要求仍在等待的请求正常成功。

所有计数是实验中的实际加载进入次数；TTL/过期时隙是逻辑时间。asyncio 的取消是协作式的，不会抢占阻塞的同步调用。没有多线程安全、跨进程共享缓存、无限重试或生产延迟保证。

