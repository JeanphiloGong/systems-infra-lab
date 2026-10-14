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
