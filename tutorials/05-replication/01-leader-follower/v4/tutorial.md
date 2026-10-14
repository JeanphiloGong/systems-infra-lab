# R01 v4: interrupted catch-up and resume

A follower can stop halfway through a log and later resume from its applied position. Re-sending already received entries is harmless because positions make delivery idempotent; a gap is rejected.

<!-- checkpoint: labs/replication/leader_follower/v4.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


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
    def __init__(self, state_path: Path | None = None) -> None:
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
        for entry in entries:
            if entry.position <= self.applied_position:
                continue
            if entry.position != self.applied_position + 1:
                raise ValueError("log gap before entry")
            self.data[entry.key] = entry.value
            self.applied_position = entry.position
            self._save()

    def catch_up(self, log: list[Entry], stop_after: int | None = None) -> None:
        end = len(log) if stop_after is None else min(stop_after, len(log))
        self.apply(log[:end])


if __name__ == "__main__":
    leader = Leader()
    leader.write("order-1", "created")
    leader.write("order-1", "paid")
    follower = Follower()
    follower.catch_up(leader.log, stop_after=1)
    follower.catch_up(leader.log)
    follower.catch_up(leader.log)
    print(follower.data, follower.applied_position)
```

