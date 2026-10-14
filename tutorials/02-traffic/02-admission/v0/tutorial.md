# F02 v0: an unbounded queue hides overload

## Pressure

If arrivals outpace workers, accepting every request only moves overload into memory and waiting time.

## Naive baseline

<!-- checkpoint: unbounded.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from threading import Lock, Thread
from time import monotonic, sleep
import tracemalloc


@dataclass(frozen=True)
class QueueObservation:
    submitted: int
    peak_queue: int
    completed: int
    peak_traced_bytes: int
    max_queue_wait_seconds: float


def observe(total: int, workers: int, service_seconds: float = 0.01) -> QueueObservation:
    if total < 1 or workers < 1 or service_seconds < 0:
        raise ValueError("invalid workload")
    queue: Queue[object] = Queue()
    completed = 0
    lock = Lock()
    waits = []
    tracemalloc.start()

    def run() -> None:
        nonlocal completed
        while True:
            item = queue.get()
            if item is None:
                queue.task_done()
                return
            with lock:
                waits.append(monotonic() - item)
            sleep(service_seconds)
            with lock:
                completed += 1
            queue.task_done()

    threads = [Thread(target=run, daemon=True) for _ in range(workers)]
    for thread in threads:
        thread.start()
    peak = 0
    for _ in range(total):
        queue.put(monotonic())
        peak = max(peak, queue.qsize())
    queue.join()
    for _ in threads:
        queue.put(None)
    for thread in threads:
        thread.join()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return QueueObservation(total, peak, completed, peak_bytes, max(waits))

result = observe(40, 1, 0.001)
assert result.completed == 40 and result.peak_queue > 1
assert result.peak_traced_bytes > 0 and result.max_queue_wait_seconds > 0
print(result)
```

## Break, check, freeze

The queue accepts all arrivals. The checkpoint measures peak queued items, maximum queue wait, and peak Python allocations using tracemalloc (not RSS or physical RAM). With one serial worker, waits grow as requests arrive faster than completion. All submitted jobs eventually complete. Run `python unbounded.py`; v1 adds an explicit capacity bound.
