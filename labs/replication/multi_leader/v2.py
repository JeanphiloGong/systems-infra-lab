from __future__ import annotations

from dataclasses import dataclass

from v0 import Network, Request


@dataclass(frozen=True)
class Version:
    timestamp_ms: int
    region: str
    sequence: int
    value: str

    @property
    def order(self) -> tuple[int, str, int]:
        return self.timestamp_ms, self.region, self.sequence


def merge(left: Version | None, right: Version) -> Version:
    if left is None or right.order > left.order:
        return right
    return left


class MultiLeader:
    def __init__(self, network: Network, offset_a: int = 0, offset_b: int = 0) -> None:
        self.network = network
        self.offsets = {"A": offset_a, "B": offset_b}
        self.sequences = {"A": 0, "B": 0}
        self.values: dict[str, Version | None] = {"A": None, "B": None}
        self.writes: list[Version] = []

    def replicate(self, source: str, target: str) -> None:
        snapshot = self.values[source]
        if snapshot is not None:
            self.network.send(source, target, lambda: self.values.__setitem__(target, merge(self.values[target], snapshot)))

    def write(self, region: str, value: str) -> Request:
        if region not in self.values:
            raise ValueError("unknown region")
        request = Request(region, value, self.network.now_ms)

        def commit() -> None:
            self.sequences[region] += 1
            version = Version(self.network.now_ms + self.offsets[region], region, self.sequences[region], value)
            self.writes.append(version)
            self.values[region] = merge(self.values[region], version)
            request.acknowledged_ms = self.network.now_ms
            self.replicate(region, "B" if region == "A" else "A")

        self.network.later(2, commit)
        self.network.run_until(request.started_ms + 100, lambda: request.acknowledged_ms is not None)
        request.finished_ms = self.network.now_ms
        return request

    def synchronize(self) -> None:
        self.replicate("A", "B")
        self.replicate("B", "A")


if __name__ == "__main__":
    net = Network()
    store = MultiLeader(net, offset_a=1000)
    net.connected = False
    early = store.write("A", "early-fast-clock")
    later = store.write("B", "later-real-time")
    net.connected = True
    store.synchronize()
    net.run_until(net.now_ms + 40, lambda: False)
    assert store.values["A"] == store.values["B"] == store.writes[0]
    print({"real_ack_ms": [early.acknowledged_ms, later.acknowledged_ms], "winner": store.values["A"].value, "lost": store.writes[1].value})
