from __future__ import annotations

from dataclasses import dataclass

from v0 import Network, Request


@dataclass(frozen=True)
class Version:
    clock: tuple[int, int]
    value: str


def dominates(left: Version, right: Version) -> bool:
    return left.clock != right.clock and all(a >= b for a, b in zip(left.clock, right.clock))


def merge(left: frozenset[Version], right: frozenset[Version]) -> frozenset[Version]:
    candidates = left | right
    return frozenset(candidate for candidate in candidates if not any(dominates(other, candidate) for other in candidates))


class MultiLeader:
    """One multi-value register with two fixed, uniquely owned writer identities."""

    def __init__(self, network: Network) -> None:
        self.network = network
        self.values: dict[str, frozenset[Version]] = {"A": frozenset(), "B": frozenset()}

    def replicate(self, source: str, target: str) -> None:
        snapshot = self.values[source]
        self.network.send(source, target, lambda: self.values.__setitem__(target, merge(self.values[target], snapshot)))

    def write(self, region: str, value: str) -> Request:
        if region not in self.values:
            raise ValueError("unknown region")
        request = Request(region, value, self.network.now_ms)

        def commit() -> None:
            current = self.values[region]
            clock = [max((entry.clock[i] for entry in current), default=0) for i in range(2)]
            clock[0 if region == "A" else 1] += 1
            self.values[region] = frozenset({Version((clock[0], clock[1]), value)})
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
    store = MultiLeader(net)
    net.connected = False
    first = store.write("A", "Alice")
    second = store.write("B", "Alicia")
    net.connected = True
    store.synchronize()
    net.run_until(net.now_ms + net.one_way_ms, lambda: False)
    assert store.values["A"] == store.values["B"] and len(store.values["A"]) == 2
    print({"latencies_ms": [first.latency_ms, second.latency_ms], "conflict": sorted(entry.value for entry in store.values["A"])})
