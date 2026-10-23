# P02 v1：增加节点不能拆开单热键

完成 v0 后，保持相同的一千次请求，只把分片数从四改成八。冷键可能重新分布，但同一个 hot 键的 900 次请求仍去同一片。节点数增加没有把这个键拆开。

本版保留 route 和 distribution，只替换 main 的实验输入。下面完整文件重复列出这两个函数，便于核对；没有新增加盐机制。

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


if __name__ == "__main__":
    keys = ["hot"] * 900 + [f"tenant-{i}" for i in range(100)]
    for partitions in (4, 8):
        loads = distribution(keys, partitions)
        assert sum(loads) == 1000
        assert max(distribution(["hot"] * 900, partitions)) == 900
        print({"partitions": partitions, "requests": loads, "hot_requests": 900})
```

```bash
uv run python -m labs.partitioning.skew.skew
```

应打印四片和八片两组分布，两组 hot_requests 都是 900。它们的总请求数仍是 1000；不要只比较平均值。下一版要拆的是业务键，而不仅是增加路由目标。

<details>
<summary>可选：参考分支验证</summary>

下面检查只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 运行，使用当时的最终接口；验证当前学习代码请运行上面的命令和内置断言。

```bash
uv run python -m pytest tests/partitioning/skew -q
```

</details>
