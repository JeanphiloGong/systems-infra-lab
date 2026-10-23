# R03 v4：用同一工作负载比较单主、多主

前面分别证明了远端单主写入成本、双主冲突、LWW 损失和计数器的专用合并规则。现在不要用“多主更快”结束，而是跑同一组请求，明确收益和代价。这里比较展示名称寄存器，不能用 v3 的无损计数结果替它背书。

## 1. 固定可比较的输入和确认口径

两种拓扑都先在 A 写 A-profile，等待一个跨区单程时间，再在 B 写 B-profile。连接正常时，等待使 B 在第二次写前看到 A；分区时等待不能传递信息。两种情况下写入的地区、顺序、值、本地 2ms 处理和 100ms 超时相同。

single 直接使用 v0 SingleLeader，multi 直接使用 v2 MultiLeader。复用已有代码，而不是在对比脚本中为不同拓扑编造耗时。完整依赖都在本章正文，源码路径保持相邻脚本导入方式。

成功延迟是 Request.finished_ms - started_ms，并检查截止前是否收到确认；超时延迟独立列出。成功样本均值不包含失败请求。分区单主成功均值也是 2ms，但只成功了一半，这不能被宣传为比分区前更快。

## 2. 只统计这个实验真正知道的冲突

连接正常时 B 已收到 A，本工作负载没有并发冲突；多主在其他工作负载中仍可能冲突。分区期间的两个成功写则确定没有互相观察，concurrent_candidates 从这两个已确认请求的不同值中计算。恢复后将这些候选与实际赢家比较，列出 discarded_conflict_values。

这不是通用的冲突检测器；它依赖当前可控投递历史，并且请求值故意唯一。生产 LWW 寄存器若只保留赢家，无法仅靠最后状态计算所有历史丢失。不要把“最终覆盖了一个因果前序值”误算成冲突丢失。

## 3. 网络恢复后再测收敛

恢复连接后，single 重发 A 当前状态到 B；multi 双向交换状态。推进有限个事件延迟后比较副本。即使均已收敛，多主分区实验仍丢失 A-profile 的并发更新。单主也有 B 地区副本，说明多地区与多主是两个不同维度。

下面是本章完整 checkpoint，包括复用的 v0、v2 和比较入口。

将下面的完整代码保存为 `labs/replication/multi_leader/v0.py`；文件已存在时，以本版内容替换该文件。

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

将下面的完整代码保存为 `labs/replication/multi_leader/v2.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/multi_leader/v2.py -->

```python
from __future__ import annotations

from dataclasses import dataclass

from v0 import Network, Request


@dataclass(frozen=True)
class Version:
    timestamp_ms: int
    region: str
    sequence: int
    value: str

    @property
    def order(self) -> tuple[int, str, int]:
        return self.timestamp_ms, self.region, self.sequence


def merge(left: Version | None, right: Version) -> Version:
    if left is None or right.order > left.order:
        return right
    return left


class MultiLeader:
    def __init__(self, network: Network, offset_a: int = 0, offset_b: int = 0) -> None:
        self.network = network
        self.offsets = {"A": offset_a, "B": offset_b}
        self.sequences = {"A": 0, "B": 0}
        self.values: dict[str, Version | None] = {"A": None, "B": None}
        self.writes: list[Version] = []

    def replicate(self, source: str, target: str) -> None:
        snapshot = self.values[source]
        if snapshot is not None:
            self.network.send(source, target, lambda: self.values.__setitem__(target, merge(self.values[target], snapshot)))

    def write(self, region: str, value: str) -> Request:
        if region not in self.values:
            raise ValueError("unknown region")
        request = Request(region, value, self.network.now_ms)

        def commit() -> None:
            self.sequences[region] += 1
            version = Version(self.network.now_ms + self.offsets[region], region, self.sequences[region], value)
            self.writes.append(version)
            self.values[region] = merge(self.values[region], version)
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
    store = MultiLeader(net, offset_a=1000)
    net.connected = False
    early = store.write("A", "early-fast-clock")
    later = store.write("B", "later-real-time")
    net.connected = True
    store.synchronize()
    net.run_until(net.now_ms + 40, lambda: False)
    assert store.values["A"] == store.values["B"] == store.writes[0]
    print({"real_ack_ms": [early.acknowledged_ms, later.acknowledged_ms], "winner": store.values["A"].value, "lost": store.writes[1].value})
```

将下面的完整代码保存为 `labs/replication/multi_leader/v4.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/multi_leader/v4.py -->

```python
from __future__ import annotations

import json

from v0 import Network, SingleLeader
from v2 import MultiLeader


def experiment(topology: str, partitioned: bool, one_way_ms: int = 40) -> dict[str, object]:
    if topology not in {"single", "multi"}:
        raise ValueError("unknown topology")
    network = Network(one_way_ms)
    store = SingleLeader(network) if topology == "single" else MultiLeader(network)
    network.connected = not partitioned
    requests = [store.write("A", "A-profile")]
    # Same caller pacing for both topologies; connected B observes A first.
    network.run_until(network.now_ms + one_way_ms, lambda: False)
    requests.append(store.write("B", "B-profile"))
    successes = [request for request in requests if request.acknowledged_ms is not None and request.acknowledged_ms <= request.finished_ms]
    successful_delays = [request.latency_ms for request in successes]
    failures = [request.latency_ms for request in requests if request not in successes]
    # These writes are known to be causally isolated only in this partition schedule.
    conflicting_values = {request.value for request in successes} if partitioned and topology == "multi" else set()
    network.connected = True
    if isinstance(store, SingleLeader):
        store.replicate()
    else:
        store.synchronize()
    network.run_until(network.now_ms + 3 * one_way_ms + 2, lambda: False)
    if isinstance(store, SingleLeader):
        converged = store.values["A"] == store.values["B"]
        winner = store.values["A"][1]
    else:
        converged = store.values["A"] == store.values["B"]
        assert store.values["A"] is not None
        winner = store.values["A"].value
    assert converged
    return {
        "topology": topology, "partitioned": partitioned,
        "attempted": len(requests), "acknowledged": len(successes),
        "success_latency_ms": successful_delays, "timeout_latency_ms": failures,
        "mean_success_ms": sum(successful_delays) / len(successful_delays) if successes else None,
        "concurrent_candidates": len(conflicting_values),
        "discarded_conflict_values": sorted(conflicting_values - {winner}),
        "converged": converged, "winner": winner,
    }


if __name__ == "__main__":
    print(json.dumps([experiment(topology, partitioned) for partitioned in (False, True) for topology in ("single", "multi")], indent=2))
```

## 4. 核对结果而不是背结论

```bash
uv run python labs/replication/multi_leader/v4.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/replication/multi_leader -q
```

</details>

默认单程 40ms 时，正常单主成功延迟是 [2,82]，多主是 [2,2]。分区后单主只有 A 成功、B 等待 100ms 超时；多主两边成功，但恢复后 LWW 丢弃 A-profile。下面检查还改变网络输入，防止“测量”退化成固定输出。

<!-- check: check_v4.py -->

```python
from v4 import experiment

for delay in (7, 40):
    single = experiment("single", False, delay)
    multi = experiment("multi", False, delay)
    assert single["success_latency_ms"] == [2, 2 * delay + 2]
    assert single["mean_success_ms"] == delay + 2
    assert multi["success_latency_ms"] == [2, 2]
    assert single["acknowledged"] == multi["acknowledged"] == 2
    assert single["concurrent_candidates"] == multi["concurrent_candidates"] == 0

single = experiment("single", True)
multi = experiment("multi", True)
assert single["acknowledged"] == 1 and single["attempted"] == 2
assert single["timeout_latency_ms"] == [100]
assert single["winner"] == "A-profile"
assert multi["acknowledged"] == 2
assert multi["concurrent_candidates"] == 2
assert multi["discarded_conflict_values"] == ["A-profile"]
assert multi["winner"] == "B-profile"
assert single["converged"] and multi["converged"]
print("v4: measured latency, availability and conflict tradeoffs passed")
```

现在的结论只适用于两个地区、单键、固定延迟、顺序请求和无持久化的模拟。没有负载队列、尾延迟分布、真实洲际网络或吞吐量测量。跨区同步持久化确认会改变延迟；地区宕机可能丢掉尚未传播的本地确认。计数器能合并不代表订单、余额或展示名称可以任意合并。

结束前应能解释：可用性来自哪个确认位置，冲突由哪段隔离历史产生，最终赢家依据什么排序，丢失列表为何不等于所有覆盖历史。R04 才进入真实 PostgreSQL 的物理和逻辑复制机制，本章不冒充那些系统的性能测试。

