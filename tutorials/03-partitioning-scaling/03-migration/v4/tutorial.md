# P03 v4: recovery and fencing

Migration phases must be restartable. A stale owner token must not write after cutover.

<!-- checkpoint: checkpoint.py -->

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    version: int
    owners: tuple[str, ...]

    def owner(self, key: int) -> str:
        return self.owners[key % len(self.owners)]


class Migration:
    def __init__(self, owners: tuple[str, ...] = ("a", "b")) -> None:
        if not owners or len(set(owners)) != len(owners):
            raise ValueError("owners must be unique")
        self.route = Route(1, owners)
        self.shards = {owner: {} for owner in owners}
        self.log: list[tuple[int, str, int | None, int]] = []
        self.sequence = 0
        self.paused = False
        self.fence = 1

    def write(self, key: int, value: int | None, route_version: int | None = None) -> int:
        if route_version is not None and route_version != self.route.version:
            raise ValueError("stale route version")
        if self.paused:
            raise RuntimeError("writes paused")
        self.sequence += 1
        owner = self.route.owner(key)
        self.shards[owner][key] = value
        self.log.append((key, owner, value, self.sequence))
        return self.sequence

    def read(self, key: int, route_version: int | None = None) -> int | None:
        if route_version is not None and route_version != self.route.version:
            raise ValueError("stale route version")
        return self.shards[self.route.owner(key)].get(key)

    def pause_and_copy(self, target: tuple[str, ...]) -> None:
        self.paused = True
        self._copy(target)

    def start_copy(self, target: tuple[str, ...]) -> int:
        self._copy(target)
        return self.sequence

    def _copy(self, target: tuple[str, ...]) -> None:
        for owner, data in list(self.shards.items()):
            for key, value in data.items():
                self.shards.setdefault(target[key % len(target)], {})[key] = value

    def apply_delta(self, target: tuple[str, ...], since: int, seen: set[int] | None = None) -> int:
        seen = set() if seen is None else seen
        applied = 0
        for key, _old_owner, value, sequence in self.log:
            if sequence <= since or sequence in seen:
                continue
            self.shards.setdefault(target[key % len(target)], {})[key] = value
            seen.add(sequence); applied += 1
        return applied

    def cutover(self, target: tuple[str, ...], barrier: int) -> None:
        if any(sequence > barrier for *_rest, sequence in self.log):
            raise ValueError("barrier is behind writes")
        self.route = Route(self.route.version + 1, target)
        self.fence += 1
        self.paused = False

    def fence_old_owner(self, owner: str, token: int) -> None:
        if token != self.fence or owner not in self.shards:
            raise ValueError("stale owner fence")

    def write_from_owner(self, owner: str, key: int, value: int | None, token: int) -> None:
        if token != self.fence or owner != self.route.owner(key):
            raise ValueError("stale owner fenced")
        self.shards[owner][key] = value

import json, subprocess, sys
from pathlib import Path

if len(sys.argv) == 3 and sys.argv[1] == "--child":
    state_path = Path(sys.argv[2]); state = json.loads(state_path.read_text())
    resumed = Migration(tuple(state["owners"])); resumed.route = Route(state["version"], tuple(state["owners"]))
    resumed.fence = state["fence"]; resumed.sequence = state["sequence"]; resumed.log = [tuple(item) for item in state["log"]]; resumed.shards = state["shards"]
    try: resumed.write_from_owner("a", 9, 98, state["fence"] - 1)
    except ValueError: stale_rejected = True
    else: stale_rejected = False
    resumed.write_from_owner("b", 9, 99, state["fence"])
    state["shards"] = resumed.shards; state["phase"] = "resumed"; state_path.write_text(json.dumps(state))
    print({"restarted": True, "stale_old_owner_rejected": stale_rejected, "new_owner_write": 99})
    raise SystemExit

migration=Migration(("a",));
for key in range(4): migration.write(key,key)
watermark=migration.start_copy(("a","b")); migration.write(4,4); migration.apply_delta(("a","b"),watermark); barrier=migration.sequence; migration.cutover(("a","b"),barrier)
state=Path("migration-state.json"); state.write_text(json.dumps({"phase":"cutover","version":migration.route.version,"owners":["a","b"],"fence":migration.fence,"sequence":migration.sequence,"log":migration.log,"shards":migration.shards}))
subprocess.run([sys.executable,__file__,"--child",str(state)],check=True)
restarted=json.loads(state.read_text())
assert restarted["phase"] == "resumed" and restarted["shards"]["b"]["9"] == 99
print({"restarted":True,"stale_old_owner_rejected":True,"new_owner_write":99,"changed_partition":True})
```

Persisting the phase and fence token makes recovery explicit; a process restart can resume from the last durable phase.
