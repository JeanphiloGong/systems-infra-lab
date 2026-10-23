# R02 v0: eventual consistency and stale reads

Asynchronous replication can return the old profile immediately after a write. Once writes stop and the pending log is applied, the replica converges.

将下面的完整代码保存为 `labs/replication/consistency/v0.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/consistency/v0.py -->

```python
from __future__ import annotations


class ReplicaSet:
    def __init__(self) -> None:
        self.leader: dict[str, str] = {}
        self.replica: dict[str, str] = {}
        self.pending: list[tuple[str, str]] = []

    def write(self, key: str, value: str) -> None:
        self.leader[key] = value
        self.pending.append((key, value))

    def read_replica(self, key: str) -> str | None:
        return self.replica.get(key)

    def apply_one(self) -> None:
        if self.pending:
            key, value = self.pending.pop(0)
            self.replica[key] = value

    def converge(self) -> None:
        while self.pending:
            self.apply_one()


if __name__ == "__main__":
    store = ReplicaSet()
    store.write("name", "Ada")
    print(store.read_replica("name"))
    store.converge()
    print(store.read_replica("name"))
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/replication/consistency/v0.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
