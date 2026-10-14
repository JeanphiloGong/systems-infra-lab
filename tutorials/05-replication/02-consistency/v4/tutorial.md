# R02 v4: compare contracts and a partition counterexample

Eventual reads favor availability, session reads preserve one client's writes, snapshots preserve a chosen version, and linearizable reads require the writer. During a partition the linearizable contract can reject the read instead of returning an unverified value.

<!-- checkpoint: labs/replication/consistency/v4.py -->

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Contract(Enum):
    EVENTUAL = "eventual"; SESSION = "session"; SNAPSHOT = "snapshot"; LINEARIZABLE = "linearizable"


@dataclass(frozen=True)
class Read:
    value: str | None
    version: int


class VersionedStore:
    def __init__(self) -> None:
        self.leader: dict[str, tuple[int, str]] = {}; self.replica: dict[str, tuple[int, str]] = {}
        self.versions: dict[str, dict[int, str]] = {}; self.partitioned = False; self.version = 0

    def write(self, key: str, value: str) -> int:
        self.version += 1; self.leader[key] = (self.version, value)
        self.versions.setdefault(key, {})[self.version] = value
        if not self.partitioned: self.replica[key] = self.leader[key]
        return self.version

    def catch_up(self) -> None:
        self.replica = dict(self.leader)

    def read(self, key: str, contract: Contract, session_version: int = 0,
             snapshot_version: int | None = None) -> Read:
        if contract is Contract.LINEARIZABLE:
            if self.partitioned: raise ConnectionError("linearizable read unavailable during partition")
            source = self.leader
        else: source = self.replica
        value = source.get(key)
        if contract is Contract.SESSION and (value is None or value[0] < session_version):
            if self.partitioned: raise ConnectionError("session read unavailable while replica is behind")
            value = self.leader.get(key)
        if contract is Contract.SNAPSHOT and snapshot_version is not None:
            available = [(v, item) for v, item in self.versions.get(key, {}).items() if v <= snapshot_version]
            if not available: return Read(None, snapshot_version)
            version, item = max(available); return Read(item, version)
        if value is None: return Read(None, 0)
        return Read(value[1], value[0])


if __name__ == "__main__":
    store = VersionedStore(); store.write("name", "Ada"); store.partitioned = True
    print(store.read("name", Contract.EVENTUAL))
    try: store.read("name", Contract.LINEARIZABLE)
    except ConnectionError as error: print(type(error).__name__)
```

