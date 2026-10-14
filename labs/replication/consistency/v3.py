from __future__ import annotations


class ReadRepairStore:
    def __init__(self) -> None:
        self.leader: dict[str, tuple[int, str]] = {}
        self.replicas: list[dict[str, tuple[int, str]]] = [{}, {}]
        self.read_history: list[tuple[int, str]] = []

    def write(self, key: str, value: str, version: int) -> None:
        self.leader[key] = (version, value)

    def seed_replica(self, index: int, key: str, version: int, value: str) -> None:
        self.replicas[index][key] = (version, value)

    def read_with_repair(self, index: int, key: str) -> tuple[int, str] | None:
        leader_value = self.leader.get(key)
        replica_value = self.replicas[index].get(key)
        if leader_value is not None and (replica_value is None or replica_value[0] < leader_value[0]):
            self.replicas[index][key] = leader_value
            replica_value = leader_value
        if replica_value is not None:
            self.read_history.append(replica_value)
        return replica_value


if __name__ == "__main__":
    store = ReadRepairStore()
    store.write("name", "Ada", 2)
    store.seed_replica(0, "name", 1, "A.")
    print(store.read_with_repair(0, "name"), store.replicas[0]["name"])
