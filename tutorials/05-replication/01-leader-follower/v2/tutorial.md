# R01 v2: read-after-write barriers

A write returns its log position. A client can read the leader immediately, or ask a follower to wait until its applied position reaches that barrier. A finite wait can time out.

<!-- checkpoint: labs/replication/leader_follower/v2.py -->

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
        self.data: dict[str, str] = {}

    def write(self, key: str, value: str) -> int:
        entry = Entry(len(self.log) + 1, key, value)
        self.log.append(entry)
        self.data[key] = value
        return entry.position


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

    def read_after(self, key: str, position: int, timeout_steps: int = 0) -> str:
        for _ in range(timeout_steps + 1):
            if self.applied_position >= position:
                return self.data[key]
            self.apply_one()
        raise TimeoutError("follower did not reach read barrier")


def read_from_leader(leader: Leader, key: str) -> str:
    return leader.data[key]


if __name__ == "__main__":
    leader = Leader()
    follower = Follower()
    position = leader.write("order-1", "paid")
    follower.receive(leader.log)
    print(read_from_leader(leader, "order-1"))
    print(follower.read_after("order-1", position, timeout_steps=1))
```

