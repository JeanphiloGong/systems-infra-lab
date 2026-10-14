# S04 v2：分别改变空间、哈希次数和插入量

前置 [v1](../v1/tutorial.md)。只测试 4096 位、5 个哈希、100 个键，不能回答“少给一半内存会怎样”或“文件增长后过滤器是否还有效”。这次保持字符串生成规则相同，遍历 m、k、n 的组合，并打印实际误报数和位数组字节数。

## 1. 概率式解释的是哪些假设

m 位，k 个近似均匀独立位置，插入 n 个不同键后，一位仍为零的概率约为 exp(-kn/m)。假设查询位置独立，假阳性率约为 (1-exp(-kn/m))**k。

这是近似公式：有限位数组、双哈希相关性、重复位置和数据分布都会带来偏差。测量使用固定字符串集合，不是独立随机重复实验；不要把一次测量与公式不相等判成 bug，也不要用极低概率时的零次误报声称永远不会误报。探测 Q 次的观测精度只有 1/Q。

新增 theoretical_false_positive_rate：m、k 必须正，n 可为零；非法参数抛错，零插入率为零。完整 filter.py 如下，原位数组算法不变。

<!-- checkpoint: labs/storage/bloom/filter.py -->
```python
from __future__ import annotations

from hashlib import blake2b
import math


class BloomFilter:
    def __init__(self, bits: int, hashes: int) -> None:
        if bits < 1 or hashes < 1:
            raise ValueError("bits and hashes must be positive")
        self.bits = bits
        self.hashes = hashes
        self.array = bytearray((bits + 7) // 8)

    def _positions(self, key: str) -> list[int]:
        digest = blake2b(key.encode("utf-8"), digest_size=16).digest()
        first = int.from_bytes(digest[:8], "little")
        second = int.from_bytes(digest[8:], "little") | 1
        return [(first + index * second) % self.bits for index in range(self.hashes)]

    def add(self, key: str) -> None:
        for position in self._positions(key):
            self.array[position // 8] |= 1 << (position % 8)

    def might_contain(self, key: str) -> bool:
        return all(self.array[position // 8] & (1 << (position % 8)) for position in self._positions(key))

    @property
    def bytes_used(self) -> int:
        return len(self.array)


def theoretical_false_positive_rate(bits: int, hashes: int, inserted: int) -> float:
    if bits < 1 or hashes < 1 or inserted < 0:
        raise ValueError("positive bits/hashes and nonnegative inserted required")
    return (1 - math.exp(-hashes * inserted / bits)) ** hashes
```

## 2. 遍历组合并保留分母

新增 measure.py 的 sweep，取三个参数列表的笛卡尔积。插入 present-i，负探测 absent-i，两组键按构造保证不重合。每行记录 bits、hashes、inserted、bytes、probes、false_positives、false_negatives、theory、measured。

false_negatives 是必须为零的正确性指标；false_positives/probes 是性能权衡指标。bytes 只代表位数组有效载荷，不是进程 RSS。sweep 不修改文件，也不使用网络。

<!-- checkpoint: labs/storage/bloom/measure.py -->
```python
from itertools import product

from labs.storage.bloom.filter import BloomFilter, theoretical_false_positive_rate


def sweep(
    bit_counts: list[int], hash_counts: list[int], insertion_counts: list[int],
    probes: int = 10000,
) -> list[dict[str, int | float]]:
    if probes < 1:
        raise ValueError("probes must be positive")
    rows: list[dict[str, int | float]] = []
    for bits, hashes, inserted in product(bit_counts, hash_counts, insertion_counts):
        theory = theoretical_false_positive_rate(bits, hashes, inserted)
        bloom = BloomFilter(bits, hashes)
        for index in range(inserted):
            bloom.add(f"present-{index}")
        false_negatives = sum(not bloom.might_contain(f"present-{index}") for index in range(inserted))
        false_positives = sum(bloom.might_contain(f"absent-{index}") for index in range(probes))
        rows.append({
            "bits": bits, "hashes": hashes, "inserted": inserted,
            "bytes": bloom.bytes_used, "probes": probes,
            "false_positives": false_positives, "false_negatives": false_negatives,
            "theory": theory, "measured": false_positives / probes,
        })
    return rows
```

下面运行八个组合：位数 512/2048，哈希 1/4，插入量 40/160。每组探测 10000 个未插入键：

```bash
uv run python - <<'PY'
from labs.storage.bloom.measure import sweep

rows = sweep([512, 2048], [1, 4], [40, 160], probes=10000)
assert len(rows) == 8
print("bits hashes inserted bytes false/probes theory measured")
for row in rows:
    assert row["false_negatives"] == 0
    assert row["bytes"] == (row["bits"] + 7) // 8
    assert row["measured"] == row["false_positives"] / row["probes"]
    print(row["bits"], row["hashes"], row["inserted"], row["bytes"],
          f'{row["false_positives"]}/{row["probes"]}',
          f'{row["theory"]:.6f}', f'{row["measured"]:.6f}')
print("v2: eight measured parameter combinations")
PY
```

预期打印八行数值和最后的成功信息。固定 k、n 增大 m 通常降低误报；固定 m、k 增大 n 使位更饱和。增大 k 并非永远有利：超过约 (m/n)*ln(2) 的常用近似最佳值会增加碰撞和 CPU 工作。这个八行实验展示变化，不把单调性对每个有限样本都成立当正确性断言。

现在知道如何报告实际成本与误报。v3 尚待 S05 v1 的真实不可变 SSTable：过滤器必须从同一个表的全部真实键构建，可能存在时仍走表查询。单独传入一份可能漏键的列表会破坏“无假阴性”，不能当成安全集成。

