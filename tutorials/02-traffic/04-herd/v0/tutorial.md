# F04 v0：同时过期，实际有多少回源在途

商品详情的热门键在逻辑时刻 5 过期。20 个请求同时进来，都先检查缓存，再查询后端。如果后端响应尚未返回，它们会全部看到同一个过期条目。先保留这个直接实现，测量真正同时等待的协程数量。

## 1. 从上一版的缺口到本版规则

Origin 是测试用的异步数据源。每次进入 load 增加 active，更新 peak；finally 在正常结束或取消时减少 active。Event 把所有已开始的加载暂停，直到实验主动放行。这测的是协程重叠，不是网络吞吐或 CPU 并行。缓存的有效条件是 now < expires；等于过期时刻就回源。

## 2. 完整 checkpoint

20 个 create_task 被安排后，sleep(0) 让它们各自执行到 Event.wait。此时没有请求能写回缓存，断言 active=peak=calls=20 才说明尖峰真实发生。release.set 后 gather 检查每个结果，最后 active 必须回到零。

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

## 3. 运行与冻结

```bash
uv run python labs/traffic/herd/v0.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/traffic/herd -q -k "[0]"
```

</details>

验收结果：实际源调用数、峰值并发均为 20；所有结果正确；活动加载数归零。 脚本中的断言会检查这些语义，pytest 还会逐字核对正文源码，写入临时目录后以独立解释器运行。本实验用 Event 和调度让出点安排交错，不依赖猜测任务已开始的固定长 sleep。

这个版本已经复现同时过期的缺陷；下一版要在首次未命中时公开一个共享填充任务，让后续同键请求等待它。

所有计数是实验中的实际加载进入次数；TTL/过期时隙是逻辑时间。asyncio 的取消是协作式的，不会抢占阻塞的同步调用。没有多线程安全、跨进程共享缓存、无限重试或生产延迟保证。

