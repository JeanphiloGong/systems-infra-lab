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
