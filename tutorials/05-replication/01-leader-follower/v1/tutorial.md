# R01 v1: delayed follower application

Replication is asynchronous: receiving an entry and applying it are separate steps. Delaying application makes a write followed immediately by a replica read visibly stale.

将下面的完整代码保存为 `labs/replication/leader_follower/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/leader_follower/v1.py -->

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    position: int
    key: str
    value: str


class Leader:
    def __init__(self) -> None:
        self.log: list[Entry] = []

    def write(self, key: str, value: str) -> Entry:
        entry = Entry(len(self.log) + 1, key, value)
        self.log.append(entry)
        return entry


class Follower:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.applied_position = 0
        self.pending: list[Entry] = []

    def receive(self, entries: list[Entry]) -> None:
        self.pending.extend(entries)

    def apply_one(self) -> None:
        if not self.pending:
            return
        entry = self.pending.pop(0)
        if entry.position != self.applied_position + 1:
            raise ValueError("log entries must be applied in order")
        self.data[entry.key] = entry.value
        self.applied_position = entry.position


if __name__ == "__main__":
    leader = Leader()
    follower = Follower()
    first = leader.write("order-1", "created")
    follower.receive([first])
    print(follower.data)
    follower.apply_one()
    print(follower.data)
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/replication/leader_follower/v1.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
