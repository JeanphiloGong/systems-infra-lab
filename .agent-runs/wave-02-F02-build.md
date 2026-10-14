# F02 build evidence

Implemented the traffic admission series under `labs/traffic/admission/`:

- v0 unbounded queue baseline and peak queue, traced allocation, and queue-wait observation.
- v1 bounded queue with explicit rejection or timeout and in-flight accounting.
- v2 lock-protected token bucket with injected clock for deterministic rate/burst checks.
- v3 explicit round-robin and least-in-flight worker selection under overlapping arrivals and heterogeneous service times.
- v4 bounded end-to-end admission with slow service, producer blocking, and p95/max latency metrics.

Tutorials live under `tutorials/02-traffic/02-admission/v0` through `v4`. `tests/traffic/admission/replay_f02.py` extracts each checkpoint to a temporary directory and executes it independently.

Verification on 2026-10-13:

```text
uv run pytest tests/traffic/admission -q
....                                                                     [100%]
4 passed in 0.09s

uv run python tests/traffic/admission/replay_f02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

The measurements are synthetic thread scheduling and queue observations. They do not claim production network throughput, physical memory usage, or fairness under arbitrary concurrent workloads.

Worker failures are caught and counted (`failed`) so a failed job cannot silently kill a worker and leave `queue.join()` blocked. In-flight accounting includes queued and executing jobs and is updated under a condition before enqueueing; a full queue rolls the reservation back.
