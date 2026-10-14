# F02 v4: slow service must propagate backpressure

## Pressure

When one worker slows down, an unbounded upstream queue hides the problem. End-to-end admission should expose wait time and rejection while keeping in-flight work bounded.

## One change

<!-- checkpoint: backpressure.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Condition, Event, Thread
from time import monotonic, sleep
from typing import Callable


@dataclass(frozen=True)
class AdmissionResult:
    accepted: int
    rejected: int
    max_in_flight: int
    wait_seconds: tuple[float, ...]


class BoundedAdmission:
    def __init__(self, capacity: int, workers: int, service_seconds: float | tuple[float, ...] = 0.01) -> None:
        delays = service_seconds if isinstance(service_seconds, tuple) else (service_seconds,) * workers
        if capacity < 1 or workers < 1 or len(delays) != workers or any(delay < 0 for delay in delays):
            raise ValueError("invalid admission bounds")
        self.queue: Queue[tuple[float, Callable[[], None]]] = Queue(maxsize=capacity)
        self._stop = Event()
        self._threads = [Thread(target=self._worker, args=(delay,), daemon=True) for delay in delays]
        self._lock = Condition()
        self.failed = 0
        self.completed = 0
        self.latencies: list[float] = []
        self._in_flight = 0
        self._max_in_flight = 0
        for thread in self._threads:
            thread.start()

    def _worker(self, delay: float) -> None:
        while not self._stop.is_set() or not self.queue.empty():
            try:
                started, job = self.queue.get(timeout=0.01)
            except Empty:
                continue
            with self._lock:
                self._lock.notify_all()
            try:
                job()
                sleep(delay)
            except Exception:
                with self._lock:
                    self.failed += 1
            else:
                with self._lock:
                    self.completed += 1
                    self.latencies.append(monotonic() - started)
            finally:
                with self._lock:
                    self._in_flight -= 1
                self.queue.task_done()

    def submit(self, job: Callable[[], None], timeout: float = 0.0) -> float | None:
        started = monotonic()
        with self._lock:
            while True:
                try:
                    self.queue.put_nowait((started, job))
                    break
                except Full:
                    remaining = timeout - (monotonic() - started)
                    if remaining <= 0:
                        return None
                    self._lock.wait(remaining)
            self._in_flight += 1
            self._max_in_flight = max(self._max_in_flight, self._in_flight)
        return monotonic() - started

    def close(self) -> None:
        self.queue.join()
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=1)

    @property
    def max_in_flight(self) -> int:
        with self._lock:
            return self._max_in_flight


def run_bounded(total: int, capacity: int, workers: int, timeout: float = 0.0) -> AdmissionResult:
    if total < 1:
        raise ValueError("total must be positive")
    admission = BoundedAdmission(capacity, workers)
    waits: list[float] = []
    accepted = rejected = 0
    try:
        for _ in range(total):
            wait = admission.submit(lambda: None, timeout=timeout)
            if wait is None:
                rejected += 1
            else:
                accepted += 1
                waits.append(wait)
    finally:
        admission.close()
    return AdmissionResult(accepted, rejected, admission.max_in_flight, tuple(waits))

for delays in ((0.002, 0.002), (0.002, 0.05)):
    admission = BoundedAdmission(2, 2, service_seconds=delays)
    started = monotonic()
    waits = [admission.submit(lambda: None, timeout=1) for _ in range(40)]
    producer_seconds = monotonic() - started
    admission.close()
    assert all(wait is not None for wait in waits)
    assert admission.completed == 40 and admission.max_in_flight <= 4
    tail = sorted(admission.latencies)[int(0.95 * (len(admission.latencies)-1))]
    print({"worker_delays": delays, "producer_seconds": producer_seconds, "max_wait": max(waits), "p95_latency": tail, "max_latency": max(admission.latencies)})
```

## Check and freeze

Both runs use two workers and 40 jobs. The second run slows one worker while keeping the other unchanged. It reports producer duration, maximum admission wait, p95 and maximum end-to-end latency, including admission wait, queue wait and service. Admission blocks the single upstream producer when capacity is full. Completion and a four-job in-flight bound are asserted. Timing observations depend on OS scheduling; no fixed speedup is asserted.
