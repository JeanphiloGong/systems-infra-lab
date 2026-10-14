# R02 v0: eventual consistency and stale reads

Asynchronous replication can return the old profile immediately after a write. Once writes stop and the pending log is applied, the replica converges.

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

