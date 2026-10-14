# R01 v0: ordered log replication

The leader appends each accepted update to a numbered log. The follower applies only the next position, so order is explicit. Restart keeps the applied checkpoint and does not replay already applied entries.

<!-- checkpoint: labs/replication/leader_follower/v0.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys


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
            if entry.position != self.applied_position + 1:
                raise ValueError("log entries must be applied in order")
            self.data[entry.key] = entry.value
            self.applied_position = entry.position
            self._save()

    def restart(self) -> None:
        """Reload the checkpoint as a process restart would."""
        if self.state_path is None:
            return
        self.data = {}
        self.applied_position = 0
        self._load()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in {"--writer", "--reader"}:
        checkpoint = Path(sys.argv[2])
        if sys.argv[1] == "--writer":
            leader = Leader()
            follower = Follower(checkpoint)
            follower.apply([leader.write("order-1", "created"), leader.write("order-1", "paid")])
            print(json.dumps({"position": follower.applied_position, "data": follower.data}))
        else:
            follower = Follower(checkpoint)
            print(json.dumps({"position": follower.applied_position, "data": follower.data}))
        raise SystemExit(0)
    leader = Leader()
    follower = Follower()
    follower.apply([leader.write("order-1", "created"), leader.write("order-1", "paid")])
    follower.restart()
    print(follower.data, follower.applied_position)
```

