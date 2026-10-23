# P02 v3：观察容量与尾部延迟边界

前版把 900 次计数写入分散到四片，但请求数不能直接当作延迟。本版使用离散队列：请求按固定间隔到达，每片一次只处理一个请求，完成时刻减去到达时刻才是本模型的延迟。输入仍是均匀、hot、加盐三类负载，另加入共享 dispatcher 的服务时间，观察瓶颈怎样转移。

保留 v2 的 `labs/partitioning/skew/skew.py`。新文件只从中导入 route，不重写路由，也不引入第二套 skew.py。simulate 返回每片请求量、每片与整体 p99、固定请求占比下的容量上界和请求总量；服务时间与到达速率是模型参数，不是生产测量。

新建 `labs/partitioning/skew/queues.py`，完整内容如下。容量上界由最忙分片占比和 service 计算；若共享 dispatcher 更慢，再取它的约束。salts 仍显式轮转子键，不能据此推导任意哈希的分布。

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

从仓库根目录执行：

```bash
uv run python -m labs.partitioning.skew.queues
```

程序打印 32 组 JSON 观测，并在最后执行对照断言：单个 hot 键从四片改成八片仍只有一片承担写入；加盐后尾延迟降低；给 dispatcher 增加服务时间又会限制容量。某项不成立时应抛 AssertionError。

这里的 p99 是固定一千个请求在本模型里的尾部分位数，不是生产延迟承诺。shared_service 为零表示没有共享服务时间，不能据此认为真实路由器没有开销；本版也没有模拟网络、失败或并发更新的读一致性。

<details>
<summary>可选：参考分支验证</summary>

旧测试只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，当前学习版使用上面的直接命令与程序末尾断言。

```bash
uv run python -m pytest tests/partitioning/skew -q
```

</details>
