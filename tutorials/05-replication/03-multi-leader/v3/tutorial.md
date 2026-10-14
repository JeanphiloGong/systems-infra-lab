# R03 v3：只增计数如何做到重复、乱序仍然收敛？

v2 的两个地区若各把访问量从 0 改成 1，LWW 最后只留下 1。直接传播“加一”也有另一种错误：网络重试让消息收到两次，就会加两次。我们需要的是一个适用于特定业务的合并规则，而不是更复杂的时间戳。

本章仅允许递增计数，不允许减法、归零、删除或“库存不能为负”约束。它是状态型 G-Counter 的两作者版本，不试图把任意业务记录变成 CRDT。

## 1. 不发送增量命令，发送每个作者的累计分量

A 只增加 A 分量，B 只增加 B 分量。每个副本保存 {A: 累计值, B: 累计值}，读取时求和。A 加 2 再加 1，B 加 4，业务结果应为 7，与地区时间无关。

snapshot 返回字典副本，必须冻结当时的数据；否则消息队列拿着同一个可变字典，后来一次写入会偷偷改变早先消息内容，乱序实验就失真。

## 2. 逐作者取 max，而不是把快照求和

收到另一个快照时，每个作者分量取 max。旧快照不能让状态倒退，重复快照不能累加；不同作者的贡献最终在求和时共同保留。逐分量 max 具有交换、结合、幂等性，这才是重复乱序不破坏结果的理由。

merge 校验快照形状和值后才修改状态；非法输入不能造成半次合并。作者身份必须唯一且自己的累计值不能在重启时归零后复用身份。这里没有持久化，真实系统需要保存分量或引入受控的新作者身份。

下面是独立的计数器 checkpoint。它承接 v2 暴露的标量损失，不依赖墙钟网络代码，因为合并性质只取决于给定快照的投递序列。

<!-- checkpoint: labs/replication/multi_leader/v3.py -->

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Counter:
    region: str
    components: dict[str, int] = field(default_factory=lambda: {"A": 0, "B": 0})

    def __post_init__(self) -> None:
        if self.region not in {"A", "B"}:
            raise ValueError("unknown writer")

    def increment(self, amount: int = 1) -> None:
        if type(amount) is not int or amount < 1:
            raise ValueError("positive integer increment required")
        self.components[self.region] += amount

    def snapshot(self) -> dict[str, int]:
        return dict(self.components)

    def merge(self, snapshot: dict[str, int]) -> None:
        if set(snapshot) != {"A", "B"} or any(type(value) is not int or value < 0 for value in snapshot.values()):
            raise ValueError("invalid counter snapshot")
        for region, value in snapshot.items():
            self.components[region] = max(self.components[region], value)

    @property
    def value(self) -> int:
        return sum(self.components.values())


if __name__ == "__main__":
    first, second = Counter("A"), Counter("B")
    first.increment(2)
    old = first.snapshot()
    first.increment()
    second.increment(4)
    first.merge(second.snapshot())
    second.merge(first.snapshot())
    second.merge(old)
    second.merge(first.snapshot())
    assert first.value == second.value == 7
    print({"value": first.value, "components": first.components})
```

## 3. 穷举投递顺序

```bash
uv run python labs/replication/multi_leader/v3.py
```

<!-- check: check_v3.py -->

```python
from itertools import permutations
from v3 import Counter

a, b = Counter("A"), Counter("B")
a.increment(2)
old_a = a.snapshot()
a.increment()
b.increment(4)
latest_a, latest_b = a.snapshot(), b.snapshot()
assert old_a == {"A": 2, "B": 0}

for delivery in permutations([old_a, latest_a, latest_b]):
    for region in ("A", "B"):
        observer = Counter(region)
        for snapshot in (*delivery, *reversed(delivery), latest_b):
            observer.merge(snapshot)
        assert observer.components == {"A": 3, "B": 4}
        assert observer.value == 7

a.merge(latest_b)
b.merge(latest_a)
assert a.components == b.components
before = a.snapshot()
for bad in ({"A": -1, "B": 4}, {"A": 3}, {"A": True, "B": 4}):
    try:
        a.merge(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid snapshot accepted")
    assert a.snapshot() == before
for amount in (0, -1, True):
    try:
        a.increment(amount)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid increment accepted")

incomplete = Counter("A")
incomplete.merge(latest_a)
assert incomplete.value == 3
incomplete.merge(latest_b)
assert incomplete.value == 7
print("v3: all six orders, duplicates, invalid inputs and eventual delivery passed")
```

这里穷举三个快照的六种顺序，每种顺序再重复和逆序投递，并在两个副本检查分量 {A:3,B:4}。只收到 A 快照仍然是 3：收敛需要最终交付 B 的最新分量，不能把幂等合并理解成“断网也自动知道别人的写入”。

G-Counter 保护的是这个只增业务的和，不会修复 v2 的展示名称，也不能替代跨地区事务。下一章回到同键寄存器，用相同工作负载比较单主与多主的确认延迟、可用性和丢失冲突。

