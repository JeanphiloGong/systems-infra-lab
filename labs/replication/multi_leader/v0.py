from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Callable


class Network:
    """Serial discrete events, in simulated milliseconds; no wall-clock sleeps."""

    def __init__(self, one_way_ms: int = 40) -> None:
        if one_way_ms < 0:
            raise ValueError("negative network delay")
        self.one_way_ms = one_way_ms
        self.now_ms = 0
        self.connected = True
        self.events: list[tuple[int, int, Callable[[], None]]] = []
        self.serial = 0
        self.trace: list[tuple[int, str]] = []

    def later(self, delay: int, action: Callable[[], None]) -> None:
        if delay < 0:
            raise ValueError("negative event delay")
        self.serial += 1
        heapq.heappush(self.events, (self.now_ms + delay, self.serial, action))

    def send(self, source: str, target: str, action: Callable[[], None]) -> None:
        cross_region = source != target
        if cross_region and not self.connected:
            self.trace.append((self.now_ms, "dropped"))
            return

        def deliver() -> None:
            if cross_region and not self.connected:
                self.trace.append((self.now_ms, "dropped"))
            else:
                self.trace.append((self.now_ms, f"deliver:{source}->{target}"))
                action()

        self.later(self.one_way_ms if cross_region else 0, deliver)

    def run_until(self, deadline: int, done: Callable[[], bool]) -> None:
        if deadline < self.now_ms:
            raise ValueError("time cannot move backwards")
        while self.events and self.events[0][0] <= deadline and not done():
            self.now_ms, _, action = heapq.heappop(self.events)
            action()
        if not done():
            self.now_ms = deadline


@dataclass
class Request:
    region: str
    value: str
    started_ms: int
    finished_ms: int | None = None
    acknowledged_ms: int | None = None

    @property
    def latency_ms(self) -> int:
        if self.finished_ms is None:
            raise RuntimeError("request still pending")
        return self.finished_ms - self.started_ms


class SingleLeader:
    def __init__(self, network: Network) -> None:
        self.network = network
        self.values: dict[str, tuple[int, str]] = {}
        self.sequence = 0

    def replicate(self) -> None:
        if "A" not in self.values:
            return
        snapshot = self.values["A"]

        def apply() -> None:
            if snapshot[0] > self.values.get("B", (0, ""))[0]:
                self.values["B"] = snapshot

        self.network.send("A", "B", apply)

    def write(self, region: str, value: str, timeout_ms: int = 100) -> Request:
        if region not in {"A", "B"} or timeout_ms < 1:
            raise ValueError("invalid request")
        request = Request(region, value, self.network.now_ms)

        def acknowledge() -> None:
            request.acknowledged_ms = self.network.now_ms

        def commit() -> None:
            self.sequence += 1
            self.values["A"] = (self.sequence, value)
            self.network.trace.append((self.network.now_ms, "commit:A"))
            self.replicate()
            self.network.send("A", region, acknowledge)

        self.network.send(region, "A", lambda: self.network.later(2, commit))
        self.network.run_until(request.started_ms + timeout_ms, lambda: request.acknowledged_ms is not None)
        request.finished_ms = self.network.now_ms
        return request


if __name__ == "__main__":
    net = Network()
    store = SingleLeader(net)
    local = store.write("A", "local")
    remote = store.write("B", "remote")
    assert (local.latency_ms, remote.latency_ms) == (2, 82)
    print({"local_ms": local.latency_ms, "remote_ms": remote.latency_ms, "trace": net.trace})
