from __future__ import annotations

from dataclasses import dataclass
from collections import deque


@dataclass
class Worker:
    name: str
    service_seconds: float


class LoadBalancer:
    def __init__(self, workers: list[Worker], strategy: str = "round_robin") -> None:
        if not workers or strategy not in {"round_robin", "least_inflight"}:
            raise ValueError("invalid workers or strategy")
        self.workers = workers
        self.strategy = strategy
        if any(worker.service_seconds <= 0 for worker in workers):
            raise ValueError("service time must be positive")
        self.latencies: list[float] = []

    def dispatch(self, count: int, arrival_interval: float = 0.01) -> dict[str, int]:
        """Simulate overlapping arrivals; each worker executes a serial FIFO."""
        if count < 1 or arrival_interval < 0:
            raise ValueError("invalid workload")
        pending = [deque() for _ in self.workers]
        self.latencies = []
        chosen: dict[str, int] = {worker.name: 0 for worker in self.workers}
        for request in range(count):
            now = request * arrival_interval
            for queue in pending:
                while queue and queue[0] <= now:
                    queue.popleft()
            index = request % len(self.workers) if self.strategy == "round_robin" else min(
                range(len(self.workers)), key=lambda i: len(pending[i])
            )
            worker = self.workers[index]
            queue = pending[index]
            finish = max(now, queue[-1] if queue else now) + worker.service_seconds
            queue.append(finish)
            self.latencies.append(finish - now)
            chosen[worker.name] += 1
        return chosen

workers = [Worker("fast", 0.01), Worker("slow", 0.1)]
rr = LoadBalancer(workers, "round_robin")
least = LoadBalancer(workers, "least_inflight")
assert rr.dispatch(100) == {"fast": 50, "slow": 50}
counts = least.dispatch(100)
assert counts["fast"] > counts["slow"] > 0
assert max(least.latencies) < max(rr.latencies)
print(counts, max(rr.latencies), max(least.latencies))
