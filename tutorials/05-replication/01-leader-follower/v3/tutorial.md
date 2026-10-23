# R01 v3: acknowledgment trade-offs

Asynchronous acknowledgment returns before the follower applies the entry, so a failed leader can lose that update. Follower acknowledgment waits for application and records a stronger confirmation boundary, with extra latency.

将下面的完整代码保存为 `labs/replication/leader_follower/v3.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/leader_follower/v3.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import time


@dataclass(frozen=True)
class Entry:
    position: int
    key: str
    value: str


class AckMode(Enum):
    ASYNC = "async"
    FOLLOWER = "follower"


class Leader:
    def __init__(self) -> None:
        self.log: list[Entry] = []
        self.data: dict[str, str] = {}
        self.confirmed_position = 0
        self.last_confirmation_latency_ms = 0.0

    def write(self, key: str, value: str, mode: AckMode, follower: "Follower") -> Entry:
        entry = Entry(len(self.log) + 1, key, value)
        self.log.append(entry)
        self.data[key] = value
        if mode is AckMode.FOLLOWER:
            started = time.perf_counter()
            follower.apply([entry])
            self.last_confirmation_latency_ms = (time.perf_counter() - started) * 1000
            self.confirmed_position = entry.position
        else:
            self.last_confirmation_latency_ms = 0.0
        return entry

    def fail_before_replication(self) -> list[Entry]:
        """Return entries that could be lost when an async leader fails."""
        return self.log[self.confirmed_position :]


class Follower:
    def __init__(self, latency_ms: float = 0.0, state_path: Path | None = None) -> None:
        if latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        self.latency_ms = latency_ms
        self.state_path = state_path
        self.data: dict[str, str] = {}
        self.applied_position = 0
        self._load()

    def _load(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        state = json.loads(self.state_path.read_text())
        self.data = dict(state["data"])
        self.applied_position = int(state["applied_position"])

    def _save(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"data": self.data, "applied_position": self.applied_position}))

    def apply(self, entries: list[Entry]) -> None:
        if self.latency_ms:
            time.sleep(self.latency_ms / 1000)
        for entry in entries:
            if entry.position != self.applied_position + 1:
                raise ValueError("log entries must be applied in order")
            self.data[entry.key] = entry.value
            self.applied_position = entry.position
            self._save()


if __name__ == "__main__":
    follower = Follower()
    leader = Leader()
    async_entry = leader.write("order-1", "created", AckMode.ASYNC, follower)
    print(async_entry.position, leader.confirmed_position, leader.fail_before_replication())
    follower.apply([async_entry])
    leader.write("order-1", "paid", AckMode.FOLLOWER, follower)
    print(follower.data)
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/replication/leader_follower/v3.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
