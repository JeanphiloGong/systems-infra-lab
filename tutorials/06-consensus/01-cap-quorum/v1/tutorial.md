# C01 v1: the Two Generals boundary

Adding acknowledgments does not create certainty: the final acknowledgment can itself be lost, and another acknowledgment would have the same problem. This trace is about unreliable communication, not a leader election algorithm.

将下面的完整代码保存为 `labs/consensus/cap_quorum/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/consensus/cap_quorum/v1.py -->

```python
from __future__ import annotations


def two_generals_trace() -> list[str]:
    """A final acknowledgment can be lost, so both sides retain uncertainty."""
    return ["A->B:attack", "B->A:ack", "ack lost", "A:uncertain", "B:uncertain"]


def conclude(trace: list[str]) -> str:
    return "coordination incomplete" if "ack lost" in trace else "trace delivered"


if __name__ == "__main__":
    trace = two_generals_trace()
    print(" | ".join(trace))
    print(conclude(trace))
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/consensus/cap_quorum/v1.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
