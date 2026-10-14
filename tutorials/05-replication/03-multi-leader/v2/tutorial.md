# R03 v2：LWW 得到同一个答案，不代表保住每次更新

v1 保留两个候选，让应用面对冲突。如果展示名称必须先返回一个字符串，可以规定确定性的 last-write-wins（LWW）。本章只替换寄存器的冲突规则，继续使用 v0 的事件网络、本地 2ms 处理及异步复制。v1 的候选集合并没有“升级为更强一致性”，而是换成了有损的标量语义。

## 1. 先定义所有副本一致认可的比较顺序

Version 保存作者墙钟时间、地区标识、作者序号和值。比较键明确为 (timestamp_ms, region, sequence)，取字典序最大项。时间相同先比较地区，地区也相同再比较递增序号，因此消息到达顺序不决定赢家。

region 唯一、序号对同一作者不重复、同一版本标识对应同一值，是该规则的输入前提。本模型只模拟恒定时钟偏移，没有处理重启后身份复用或钟表回拨。不要把这三个字段叫成真实全局时间顺序。

## 2. 把偏差放进时钟，把真实先后留在事件轴上

A 的钟固定快 1000ms。A 在事件时间 2ms 确认 early-fast-clock，版本时间是 1002；B 在事件时间 4ms 确认 later-real-time，版本时间是 4。分区期间两个用户都成功了。恢复后 merge 在两个方向都选 A，真实较晚的 B 写入从当前寄存器中消失。

writes 仅用于实验追踪全部本地生成版本，不参加合并或恢复，也不表示生产副本会保留历史。应用不能把这个辅助观测列表误当成“丢失更新已被系统自动恢复”。

## 3. 在确认语义里承认损失

write 确认的是本地生成并接受一次尝试，不保证它最终赢得 LWW。慢钟地区若已经看到快钟地区的高时间戳，其新写甚至会在本地立即输掉。本章把这种结果暴露为规则代价，不承诺跨地区 read-your-writes 或线性一致。

下面是完整 checkpoint，保留事件追踪和版本比较两条独立的时间解释。

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

## 4. 验证有损收敛

```bash
uv run python labs/replication/multi_leader/v2.py
```

<!-- check: check_v2.py -->

```python
from v0 import Network
from v2 import MultiLeader, Version, merge

a = Version(10, "A", 1, "a")
b = Version(10, "B", 1, "b")
assert merge(a, b) == merge(b, a) == b
assert merge(b, b) == b
assert merge(Version(10, "A", 1, "a"), Version(10, "A", 2, "next")).value == "next"

net = Network()
store = MultiLeader(net, offset_a=1000)
net.connected = False
first = store.write("A", "early")
second = store.write("B", "late")
assert first.acknowledged_ms == 2 < second.acknowledged_ms == 4
assert store.writes[0].timestamp_ms == 1002
assert store.writes[1].timestamp_ms == 4
net.connected = True
store.synchronize()
net.run_until(net.now_ms + 40, lambda: False)
assert store.values["A"] == store.values["B"] == store.writes[0]
assert store.writes[1] not in store.values.values()
for version in reversed(store.writes * 3):
    store.values["B"] = merge(store.values["B"], version)
assert store.values["B"] == store.writes[0]

slow = store.write("B", "slow-clock-new-write")
assert slow.acknowledged_ms is not None
assert store.values["B"].value == "early"
print("v2: deterministic ties, skew loss and duplicate checks passed")
```

运行后要同时检查真实确认时间 [2,4] 与 winner=early-fast-clock，才能证明这是时钟偏移导致的更新损失，而不只是两个常量的比较。固定时间戳冲突检查还验证了交换顺序和重复传播不改变赢家。

LWW 适用于愿意接受该覆盖语义的字段，不适合把两个地区“各加 1”直接当作同一个整数寄存器覆盖。下一章会限制业务为只增计数，换取无重复累加的合并规则。

