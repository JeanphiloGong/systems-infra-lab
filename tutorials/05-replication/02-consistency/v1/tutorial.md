# R02 v1: session read-your-writes

A session records the version it wrote. If its replica is behind that version, the session reads the leader, while another client can still observe the old replica value.

将下面的完整代码保存为 `labs/replication/consistency/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/consistency/v1.py -->

```python
from __future__ import annotations


class ReplicaSet:
    def __init__(self) -> None:
        self.leader: dict[str, tuple[int, str]] = {}
        self.replica: dict[str, tuple[int, str]] = {}
        self.pending: list[tuple[str, int, str]] = []
        self.version = 0

    def write(self, key: str, value: str) -> int:
        self.version += 1
        self.leader[key] = (self.version, value)
        self.pending.append((key, self.version, value))
        return self.version

    def read_replica(self, key: str) -> tuple[int, str] | None:
        return self.replica.get(key)

    def apply_one(self) -> None:
        if self.pending:
            key, version, value = self.pending.pop(0)
            self.replica[key] = (version, value)

    def read_your_writes(self, key: str, session_version: int) -> tuple[int, str] | None:
        value = self.replica.get(key)
        if value is None or value[0] < session_version:
            return self.leader.get(key)
        return value


class Session:
    def __init__(self) -> None:
        self.written_version = 0

    def write(self, store: ReplicaSet, key: str, value: str) -> int:
        self.written_version = store.write(key, value)
        return self.written_version

    def read(self, store: ReplicaSet, key: str) -> tuple[int, str] | None:
        return store.read_your_writes(key, self.written_version)


if __name__ == "__main__":
    store = ReplicaSet()
    session = Session()
    session.write(store, "name", "Ada")
    print(session.read(store, "name"), store.read_replica("name"))
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/replication/consistency/v1.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
