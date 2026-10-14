# P02 v3：观察容量与尾部延迟边界

本版使用可重复的离散队列模型测量固定批次的p99、每分片请求量和容量上界。均匀键分布和固定hot键分布都记录每个分片请求量；加盐显式轮转子键，共享dispatcher瓶颈会重新限制容量。

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

```python
from labs.partitioning.skew.queues import simulate

report = simulate(["hot"] * 1000, partitions=8, arrival_rate=2, salts=8)
assert report["total"] == 1000
print(report)
```

完整队列模型在 `labs/partitioning/skew/queues.py`，运行：

```bash
uv run python -m labs.partitioning.skew.skew --partitions 4
uv run python -m labs.partitioning.skew.queues
uv run python -m pytest tests/partitioning/skew -q
```

v3验证单热键加节点仍在同一队列，加盐后p99和容量边界改善，共享瓶颈重新限制容量。service=1和固定1000请求只是模型单位，不是生产p99承诺。
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
<!-- checkpoint: labs/partitioning/skew/queues.py -->

```python
from __future__ import annotations

import json
from math import ceil, isfinite

from labs.partitioning.skew.skew import route


def simulate(keys: list[str], partitions: int, arrival_rate: float, service: float = 1.0, shared_service: float = 0.0, salts: int = 0) -> dict[str, object]:
    if partitions < 1 or salts < 0 or not isfinite(arrival_rate) or arrival_rate <= 0 or not isfinite(service) or service <= 0 or not isfinite(shared_service) or shared_service < 0:
        raise ValueError("invalid queue model parameter")
    busy = [0.0] * partitions
    latencies: list[list[float]] = [[] for _ in range(partitions)]
    counts = [0] * partitions
    dispatcher = 0.0
    hot_index = 0
    for index, key in enumerate(keys):
        arrival = index / arrival_rate
        if key == "hot" and salts:
            shard = hot_index % salts % partitions
            hot_index += 1
        else:
            shard = route(key, partitions)
        dispatcher = max(dispatcher, arrival) + shared_service
        finish = max(busy[shard], dispatcher) + service
        busy[shard] = finish
        counts[shard] += 1
        latencies[shard].append(finish-arrival)
    def p99(values: list[float]) -> float:
        return sorted(values)[ceil(len(values)*0.99)-1] if values else 0.0
    fractions = [count/len(keys) for count in counts] if keys else []
    ceiling = 1/(max(fractions)*service) if fractions else None
    if ceiling is not None and shared_service:
        ceiling = min(ceiling, 1/shared_service)
    return {"requests": counts, "p99_by_shard": [p99(values) for values in latencies],
            "p99": p99([value for values in latencies for value in values]),
            "capacity_bound": ceiling, "total": sum(counts)}


def main() -> None:
    uniform = [f"k{index%256}" for index in range(1000)]
    hot = ["hot" if index%10 else f"cold{index}" for index in range(1000)]
    for rate in (0.5, 1.0, 2.0, 4.0):
        for partitions in (4, 8):
            for workload, keys, salts, shared in (("uniform", uniform, 0, 0.0), ("hot", hot, 0, 0.0), ("split", hot, 8, 0.0), ("shared", hot, 8, 1.0)):
                print(json.dumps({"workload":workload,"nodes":partitions,"arrival_rate":rate,
                                  **simulate(keys, partitions, rate, salts=salts, shared_service=shared)}))

    unsalted_four = simulate(["hot"] * 1000, 4, 2)
    unsalted_eight = simulate(["hot"] * 1000, 8, 2)
    salted = simulate(["hot"] * 1000, 8, 2, salts=8)
    shared = simulate(["hot"] * 1000, 8, 2, salts=8, shared_service=1)
    assert unsalted_four["p99"] == unsalted_eight["p99"]
    assert salted["p99"] < unsalted_eight["p99"] and salted["capacity_bound"] > unsalted_eight["capacity_bound"]
    assert shared["capacity_bound"] == 1 and shared["p99"] > salted["p99"]


if __name__ == "__main__":
    main()

```
from __future__ import annotations

import json
from math import ceil, isfinite

from labs.partitioning.skew.skew import route


def simulate(keys: list[str], partitions: int, arrival_rate: float, service: float = 1.0, shared_service: float = 0.0, salts: int = 0) -> dict[str, object]:
    if partitions < 1 or salts < 0 or not isfinite(arrival_rate) or arrival_rate <= 0 or not isfinite(service) or service <= 0 or not isfinite(shared_service) or shared_service < 0:
        raise ValueError("invalid queue model parameter")
    busy = [0.0] * partitions
    latencies: list[list[float]] = [[] for _ in range(partitions)]
    counts = [0] * partitions
    dispatcher = 0.0
    hot_index = 0
    for index, key in enumerate(keys):
        arrival = index / arrival_rate
        if key == "hot" and salts:
            shard = hot_index % salts % partitions
            hot_index += 1
        else:
            shard = route(key, partitions)
        dispatcher = max(dispatcher, arrival) + shared_service
        finish = max(busy[shard], dispatcher) + service
        busy[shard] = finish
        counts[shard] += 1
        latencies[shard].append(finish-arrival)
    def p99(values: list[float]) -> float:
        return sorted(values)[ceil(len(values)*0.99)-1] if values else 0.0
    fractions = [count/len(keys) for count in counts] if keys else []
    ceiling = 1/(max(fractions)*service) if fractions else None
    if ceiling is not None and shared_service:
        ceiling = min(ceiling, 1/shared_service)
    return {"requests": counts, "p99_by_shard": [p99(values) for values in latencies],
            "p99": p99([value for values in latencies for value in values]),
            "capacity_bound": ceiling, "total": sum(counts)}


def main() -> None:
    uniform = [f"k{index%256}" for index in range(1000)]
    hot = ["hot" if index%10 else f"cold{index}" for index in range(1000)]
    for rate in (0.5, 1.0, 2.0, 4.0):
        for partitions in (4, 8):
            for workload, keys, salts, shared in (("uniform", uniform, 0, 0.0), ("hot", hot, 0, 0.0), ("split", hot, 8, 0.0), ("shared", hot, 8, 1.0)):
                print(json.dumps({"workload":workload,"nodes":partitions,"arrival_rate":rate,
                                  **simulate(keys, partitions, rate, salts=salts, shared_service=shared)}))


if __name__ == "__main__":
    main()

```
