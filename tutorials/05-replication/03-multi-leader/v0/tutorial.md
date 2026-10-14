# R03 v0：远端写入到底多等了多久？

A 地区保存个人展示名称，B 地区用户也能修改它。先沿用 R01 的单主：任何写入都在 A 执行，B 只是异步读取副本。用户在 A 发起请求只经过本地处理；用户在 B 发起请求必须先把消息送到 A，再等确认回来。多地区部署因此不代表多主。

本章把跨区单程延迟假设为 40 模拟毫秒、本地处理假设为 2 模拟毫秒。它们是可修改的输入，不是现实地区的测速结果。要测的是“调用开始到确认事件”的时间差，而不是把 82 直接写进测量字段。

## 1. 让延迟由消息实际走过的路径产生

直接修改字典无法表达消息何时送达。Network 用最小堆保存未来事件，键是时间和递增序号；同一时刻按入队次序运行，避免比较函数对象。run_until 只推进到下一事件，不 sleep，也不读取墙钟。日志留下实际执行的送达与提交时间。没有事件满足确认条件时，时间推进到请求的截止点。

send 同时检查发出和送达时的连通性。分区丢弃消息，不替应用自动重试；恢复后由复制逻辑重发当前状态。这正是 C01 的边界：网络恢复不等于已丢消息自动出现。

## 2. 保留一个真正的单主写入口

write 记录开始时间，向 A 发送请求，在 A 的 2ms 处理结束后修改值，再发送确认。replicate 独立发送带序号的快照到 B，旧快照不能覆盖新快照。客户端确认不等待副本，因此延迟口径是主节点完成并确认，而不是跨区持久化确认。

Request 同时记录客户端停止等待的时间和确认到达时间。如果跨区非常慢，客户端先超时，A 仍可能稍后完成写入；超时不能声称“业务一定未发生”。本章不实现去重与取消。

下面是本版本完整 checkpoint，保存到注释所列路径；下一版本会直接复用这里的事件网络和请求记录。

<!-- checkpoint: labs/replication/multi_leader/v0.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Callable


class Network:
    """Serial discrete events, in simulated milliseconds; no wall-clock sleeps."""

    def __init__(self, one_way_ms: int = 40) -> None:
        if one_way_ms < 0:
            raise ValueError("negative network delay")
        self.one_way_ms = one_way_ms
        self.now_ms = 0
        self.connected = True
        self.events: list[tuple[int, int, Callable[[], None]]] = []
        self.serial = 0
        self.trace: list[tuple[int, str]] = []

    def later(self, delay: int, action: Callable[[], None]) -> None:
        if delay < 0:
            raise ValueError("negative event delay")
        self.serial += 1
        heapq.heappush(self.events, (self.now_ms + delay, self.serial, action))

    def send(self, source: str, target: str, action: Callable[[], None]) -> None:
        cross_region = source != target
        if cross_region and not self.connected:
            self.trace.append((self.now_ms, "dropped"))
            return

        def deliver() -> None:
            if cross_region and not self.connected:
                self.trace.append((self.now_ms, "dropped"))
            else:
                self.trace.append((self.now_ms, f"deliver:{source}->{target}"))
                action()

        self.later(self.one_way_ms if cross_region else 0, deliver)

    def run_until(self, deadline: int, done: Callable[[], bool]) -> None:
        if deadline < self.now_ms:
            raise ValueError("time cannot move backwards")
        while self.events and self.events[0][0] <= deadline and not done():
            self.now_ms, _, action = heapq.heappop(self.events)
            action()
        if not done():
            self.now_ms = deadline


@dataclass
class Request:
    region: str
    value: str
    started_ms: int
    finished_ms: int | None = None
    acknowledged_ms: int | None = None

    @property
    def latency_ms(self) -> int:
        if self.finished_ms is None:
            raise RuntimeError("request still pending")
        return self.finished_ms - self.started_ms


class SingleLeader:
    def __init__(self, network: Network) -> None:
        self.network = network
        self.values: dict[str, tuple[int, str]] = {}
        self.sequence = 0

    def replicate(self) -> None:
        if "A" not in self.values:
            return
        snapshot = self.values["A"]

        def apply() -> None:
            if snapshot[0] > self.values.get("B", (0, ""))[0]:
                self.values["B"] = snapshot

        self.network.send("A", "B", apply)

    def write(self, region: str, value: str, timeout_ms: int = 100) -> Request:
        if region not in {"A", "B"} or timeout_ms < 1:
            raise ValueError("invalid request")
        request = Request(region, value, self.network.now_ms)

        def acknowledge() -> None:
            request.acknowledged_ms = self.network.now_ms

        def commit() -> None:
            self.sequence += 1
            self.values["A"] = (self.sequence, value)
            self.network.trace.append((self.network.now_ms, "commit:A"))
            self.replicate()
            self.network.send("A", region, acknowledge)

        self.network.send(region, "A", lambda: self.network.later(2, commit))
        self.network.run_until(request.started_ms + timeout_ms, lambda: request.acknowledged_ms is not None)
        request.finished_ms = self.network.now_ms
        return request


if __name__ == "__main__":
    net = Network()
    store = SingleLeader(net)
    local = store.write("A", "local")
    remote = store.write("B", "remote")
    assert (local.latency_ms, remote.latency_ms) == (2, 82)
    print({"local_ms": local.latency_ms, "remote_ms": remote.latency_ms, "trace": net.trace})
```

## 3. 运行并检查这个 checkpoint

```bash
uv run python labs/replication/multi_leader/v0.py
uv run python -m pytest tests/replication/multi_leader -q
```

下面的检查由 replay 从正文提取到源码同目录执行，不从仓库补齐依赖。

<!-- check: check_v0.py -->

```python
from v0 import Network, SingleLeader

for delay in (0, 7, 40):
    net = Network(delay)
    store = SingleLeader(net)
    local = store.write("A", "local")
    remote = store.write("B", "remote")
    assert local.latency_ms == 2
    assert remote.latency_ms == 2 * delay + 2
    assert remote.acknowledged_ms == remote.finished_ms
    net.run_until(net.now_ms + delay, lambda: False)
    assert store.values["A"] == store.values["B"]
    assert sum(event == "commit:A" for _, event in net.trace) == 2

net = Network(80)
store = SingleLeader(net)
timed_out = store.write("B", "eventually-applied", timeout_ms=50)
assert timed_out.acknowledged_ms is None
net.run_until(200, lambda: False)
assert store.values["A"][1] == "eventually-applied"
assert timed_out.acknowledged_ms == 162
assert timed_out.latency_ms == 50

net = Network()
store = SingleLeader(net)
net.connected = False
unavailable = store.write("B", "blocked")
assert unavailable.acknowledged_ms is None and unavailable.latency_ms == 100
assert store.values == {}
print("v0: measured WAN cost, late effect and partition checks passed")
```

检查把单程延迟改成 0、7、40，确认远端请求分别走 2、16、82ms 的路径。另一个检查让客户端在 50ms 超时，但 A 在 82ms 提交、确认在 162ms 到达：不要把失败响应等同于没有副作用。

当前只处理一个键、顺序发起的请求，没有排队竞争、CPU 开销、磁盘或丢包重试，不能据此推算吞吐量或真实 p99。下一章的压力是：A/B 分区时，B 用户连本地修改也无法确认。让 B 本地接受写入会带来什么冲突？

