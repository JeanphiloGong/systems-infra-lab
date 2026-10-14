# R03 v1：两边都能写，但一个名字变成两个版本

v0 在分区时无法确认 B 的写入。现在 A 和 B 都维护自己的可写副本：本地处理 2ms 后即可确认，跨区传播在确认之后进行。用户体验改善了，但 Alice 与 Alicia 两次同键修改可能互相没有见过。不能因为其中一个消息最后送到，就悄悄抹掉另一个。

沿用 v0 的 Network 和 Request；下面重新打印完整依赖，便于在空目录复现。它们不包含未来的冲突解决逻辑。

## 1. 区分“看到之后修改”和“彼此不知道的修改”

一个整数序号只能表达单主顺序。两个作者用向量 (A 次数, B 次数) 表示当前版本已经吸收的历史。在分区下，A 生成 (1,0)，B 生成 (0,1)：双方都不能逐分量覆盖另一个，所以是并发版本。这里的并发是因果并发，即使模拟器依次调用两个 write，也不代表 B 看到了 A。

如果 B 先接收了 A 的 (1,0)，再写入，就生成 (1,1)，可以覆盖 (1,0)。dominates 必须至少一个分量更大，其余分量不能更小；相同向量不算严格覆盖。

## 2. 合并的是候选集合，不是随便选一个值

merge 先取集合并，再删除被其他版本因果覆盖的项。重复消息天然去重，互不覆盖的项留下来。每个地区本地写入时，读取当前候选的逐分量最大值，增加自己的分量，把本地候选替换为新版本。这表示应用明确覆盖了它当时看到的所有候选，不是自动字符串拼接。

replicate 捕获不可变快照并安排网络事件。分区下传播被丢弃，但本地确认仍成功。恢复网络后 synchronize 重发两边的当前状态；不执行这个步骤就没有收敛保证。下面是本章完整 checkpoint。

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

<!-- checkpoint: labs/replication/multi_leader/v1.py -->

```python
from __future__ import annotations

from dataclasses import dataclass

from v0 import Network, Request


@dataclass(frozen=True)
class Version:
    clock: tuple[int, int]
    value: str


def dominates(left: Version, right: Version) -> bool:
    return left.clock != right.clock and all(a >= b for a, b in zip(left.clock, right.clock))


def merge(left: frozenset[Version], right: frozenset[Version]) -> frozenset[Version]:
    candidates = left | right
    return frozenset(candidate for candidate in candidates if not any(dominates(other, candidate) for other in candidates))


class MultiLeader:
    """One multi-value register with two fixed, uniquely owned writer identities."""

    def __init__(self, network: Network) -> None:
        self.network = network
        self.values: dict[str, frozenset[Version]] = {"A": frozenset(), "B": frozenset()}

    def replicate(self, source: str, target: str) -> None:
        snapshot = self.values[source]
        self.network.send(source, target, lambda: self.values.__setitem__(target, merge(self.values[target], snapshot)))

    def write(self, region: str, value: str) -> Request:
        if region not in self.values:
            raise ValueError("unknown region")
        request = Request(region, value, self.network.now_ms)

        def commit() -> None:
            current = self.values[region]
            clock = [max((entry.clock[i] for entry in current), default=0) for i in range(2)]
            clock[0 if region == "A" else 1] += 1
            self.values[region] = frozenset({Version((clock[0], clock[1]), value)})
            request.acknowledged_ms = self.network.now_ms
            self.replicate(region, "B" if region == "A" else "A")

        self.network.later(2, commit)
        self.network.run_until(request.started_ms + 100, lambda: request.acknowledged_ms is not None)
        request.finished_ms = self.network.now_ms
        return request

    def synchronize(self) -> None:
        self.replicate("A", "B")
        self.replicate("B", "A")


if __name__ == "__main__":
    net = Network()
    store = MultiLeader(net)
    net.connected = False
    first = store.write("A", "Alice")
    second = store.write("B", "Alicia")
    net.connected = True
    store.synchronize()
    net.run_until(net.now_ms + net.one_way_ms, lambda: False)
    assert store.values["A"] == store.values["B"] and len(store.values["A"]) == 2
    print({"latencies_ms": [first.latency_ms, second.latency_ms], "conflict": sorted(entry.value for entry in store.values["A"])})
```

## 3. 运行和复现冲突

```bash
uv run python labs/replication/multi_leader/v1.py
```

<!-- check: check_v1.py -->

```python
from v0 import Network
from v1 import MultiLeader, Version, dominates, merge

a = frozenset({Version((1, 0), "Alice")})
b = frozenset({Version((0, 1), "Alicia")})
assert not dominates(next(iter(a)), next(iter(b)))
assert merge(a, b) == merge(b, a) == a | b
assert merge(merge(a, b), a) == a | b

net = Network()
store = MultiLeader(net)
net.connected = False
first = store.write("A", "Alice")
second = store.write("B", "Alicia")
assert [first.latency_ms, second.latency_ms] == [2, 2]
assert len(store.values["A"]) == len(store.values["B"]) == 1
net.connected = True
store.synchronize()
net.run_until(net.now_ms + 40, lambda: False)
assert store.values["A"] == store.values["B"] == a | b
store.write("A", "chosen-by-user")
net.run_until(net.now_ms + 40, lambda: False)
expected = frozenset({Version((2, 1), "chosen-by-user")})
assert store.values["A"] == store.values["B"] == expected
assert merge(expected, a) == expected
print("v1: local acknowledgments, causal overwrite and conflict checks passed")
```

这次的收敛结果是“两个地区都知道有两个候选”，不是“已经得到一个名字”。页面需要提示冲突或提供业务解决入口；测试随后让用户明确写入 chosen-by-user，才使两个候选被一个因果更新取代。

固定 A/B 身份、各作者顺序写、身份不重用和内存状态不重置是本章前提。没有持久化、认证或任意成员变更，也没有通过时钟估算因果。下一章会选择一个确定性单值规则，并检查它会丢掉什么。

