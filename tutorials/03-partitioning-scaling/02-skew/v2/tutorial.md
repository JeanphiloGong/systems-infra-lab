# P02 v2：对子键计数做加盐

本版使用可重复的整数请求计数模型。均匀键分布和固定hot键分布都记录每个分片请求量，不能只看平均值。加盐策略显式把子键轮转到分片，不承诺任意哈希会均匀；读取聚合必须遍历所有子键。

完整 checkpoint `labs/partitioning/skew/skew.py`：

```python
from __future__ import annotations

from collections import Counter
import hashlib
from typing import Iterable


def route(key: str, partitions: int) -> int:
    if partitions < 1:
        raise ValueError("partitions must be positive")
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") % partitions


def distribution(keys: Iterable[str], partitions: int) -> list[int]:
    counts = [0] * partitions
    for key in keys:
        counts[route(key, partitions)] += 1
    return counts


def salted_counts(key: str, writes: int, salts: int, partitions: int) -> list[int]:
    if writes < 0 or salts < 1:
        raise ValueError("writes must be nonnegative and salts positive")
    counts = [0] * partitions
    for index in range(writes):
        counts[index % salts % partitions] += 1
    return counts


def aggregate(keys: Iterable[str], partitions: int) -> tuple[list[int], int]:
    counts = distribution(keys, partitions)
    return counts, sum(counts)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--partitions", type=int, default=4)
    parser.add_argument("--hot-writes", type=int, default=900)
    args = parser.parse_args()
    uniform = [f"tenant-{index}" for index in range(1000)]
    skewed = ["hot"] * args.hot_writes + [f"tenant-{index}" for index in range(100)]
    print({"uniform": distribution(uniform, args.partitions), "skewed": distribution(skewed, args.partitions)})
    print({"hot_salted": salted_counts("hot", args.hot_writes, args.partitions, args.partitions)})


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.partitioning.skew.skew --partitions 4
uv run python -m pytest tests/partitioning/skew -q
```

v2 的验证是请求总量守恒、单个热键只能由一个分片处理、加盐后汇总不丢失。此模型不包含网络或数据库延迟，不能把分片请求数量直接解释为真实p99；容量需结合实际服务时间测量。
<!-- checkpoint: labs/partitioning/skew/skew.py -->

```python
from __future__ import annotations

import hashlib
from typing import Iterable


def route(key: str, partitions: int) -> int:
    if partitions < 1:
        raise ValueError("partitions must be positive")
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") % partitions


def distribution(keys: Iterable[str], partitions: int) -> list[int]:
    if partitions < 1:
        raise ValueError("partitions must be positive")
    counts = [0] * partitions
    for key in keys:
        counts[route(key, partitions)] += 1
    return counts


def salted_counts(key: str, writes: int, salts: int, partitions: int) -> list[int]:
    if writes < 0 or salts < 1 or partitions < 1:
        raise ValueError("writes must be nonnegative; salts and partitions positive")
    counts = [0] * partitions
    for index in range(writes):
        counts[index % salts % partitions] += 1
    return counts


def profile(keys: Iterable[str], partitions: int) -> dict[str, list[int]]:
    requests = list(keys)
    return {"distinct_keys": distribution(set(requests), partitions), "requests": distribution(requests, partitions)}


def split_counter(writes: int, salts: int, partitions: int) -> tuple[list[int], int, int]:
    if writes < 0 or salts < 1 or partitions < 1:
        raise ValueError("invalid counter size")
    shards: list[dict[int, int]] = [{} for _ in range(partitions)]
    loads = [0] * partitions
    for index in range(writes):
        subkey = index % salts
        shard = subkey % partitions
        shards[shard][subkey] = shards[shard].get(subkey, 0) + 1
        loads[shard] += 1
    total = sum(shards[subkey % partitions].get(subkey, 0) for subkey in range(salts))
    return loads, total, salts


def aggregate(keys: Iterable[str], partitions: int) -> tuple[list[int], int]:
    counts = distribution(keys, partitions)
    return counts, sum(counts)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--partitions", type=int, default=4)
    parser.add_argument("--hot-writes", type=int, default=900)
    args = parser.parse_args()
    uniform = [f"tenant-{index}" for index in range(1000)]
    skewed = ["hot"] * args.hot_writes + [f"tenant-{index}" for index in range(100)]
    print({"uniform": distribution(uniform, args.partitions), "skewed": distribution(skewed, args.partitions)})
    print({"hot_salted": salted_counts("hot", args.hot_writes, args.partitions, args.partitions)})


if __name__ == "__main__":
    main()

```
