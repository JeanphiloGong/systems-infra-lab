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
