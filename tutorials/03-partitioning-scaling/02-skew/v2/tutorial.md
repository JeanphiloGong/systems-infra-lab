# P02 v2：对子键计数做加盐

v1 已经证明单个 hot 键不会随节点增多而拆开。本版把一个可加和计数器拆成四个子计数器：每次增量轮流写入一个子键，读取总数时必须把四个子键全部读出再求和。

这是一种会改变读写契约的选择，不适用于必须原子读取单值的任意对象。教学模型显式规定子键编号对分片数取模，不声称任意哈希都能把四个子键完美分散。split_counter 创建本次实验的四个存储位置并返回每片写入数、求和结果和读取子键次数；它不修改真实服务。

先从仓库根目录执行 `uv sync --locked`。创建父目录后，完整替换 `labs/partitioning/skew/skew.py`：

<!-- checkpoint: labs/partitioning/skew/skew.py -->

```python
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


if __name__ == "__main__":
    assert max(distribution(["hot"] * 900, 4)) == 900
    loads, total, reads = split_counter(900, salts=4, partitions=4)
    assert loads == [225, 225, 225, 225] and total == 900 and reads == 4
    assert split_counter(0, salts=4, partitions=4) == ([0, 0, 0, 0], 0, 4)
    print({"writes_by_shard": loads, "total": total, "read_subkeys": reads})
```

```bash
uv run python -m labs.partitioning.skew.skew
```

应打印 writes_by_shard 为 [225, 225, 225, 225]，total 为 900，read_subkeys 为 4。写入压力分散的代价是读放大和跨子键一致性问题；本版只验证可加和整数、单进程执行。下一版通过明确的服务时间与到达间隔观察排队，而不把本版计数直接当作 p99。

<details>
<summary>可选：参考分支验证</summary>

下面检查只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 运行，使用当时的最终接口；验证当前学习代码请运行上面的命令和内置断言。

```bash
uv run python -m pytest tests/partitioning/skew -q
```

</details>
