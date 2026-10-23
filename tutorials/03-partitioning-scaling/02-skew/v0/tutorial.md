# P02 v0：建立均匀与倾斜分布

一千次请求分到四个分片，平均每片 250 次并不意味着负载均匀。若 900 次都访问同一个 hot 键，那个键只会路由到一片。先比较“不同键数量”和“请求数量”，不引入加盐或队列。

使用固定 SHA-256 路由，避免 Python 内置 hash 的进程随机化影响对照。distribution 接收实际请求序列并逐次计数；将 set(keys) 作为输入时，测量的是不同键的数量，而非请求量。

先从仓库根目录执行 `uv sync --locked`。创建父目录后，新建 `labs/partitioning/skew/skew.py`：

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


if __name__ == "__main__":
    uniform = [f"tenant-{i}" for i in range(1000)]
    skewed = ["hot"] * 900 + [f"tenant-{i}" for i in range(100)]
    for name, keys in [("uniform", uniform), ("skewed", skewed)]:
        loads = distribution(keys, 4)
        assert sum(loads) == 1000
        print(name, {"distinct_keys": distribution(set(keys), 4), "requests": loads})
    assert max(distribution(["hot"] * 900, 4)) == 900
```

```bash
uv run python -m labs.partitioning.skew.skew
```

两种输入的 requests 总和都应为 1000。skewed 中有一片至少承受 900 次请求，尽管不同键的数量没有同等程度的倾斜。实际每片数字由固定样例计算，不是预设的硬件吞吐。下一版只增加分片数，对照热点是否消失。

<details>
<summary>可选：参考分支验证</summary>

下面检查只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 运行，使用当时的最终接口；验证当前学习代码请运行上面的命令和内置断言。

```bash
uv run python -m pytest tests/partitioning/skew -q
```

</details>
