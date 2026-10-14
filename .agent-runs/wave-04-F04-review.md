# F04 independent review

Verdict: **pass**.

## Evidence

The author replaced the sequential draft with real asyncio tasks. `uv run
pytest tests/traffic/herd -q` returned **4 passed in 0.76s**. The tests extract
the complete source fences for v0-v3 into a fresh directory, verify each fence
matches its source file, and execute each checkpoint with a new interpreter.

The experiments verify synchronized different-key expiry (actual peak 20),
same-key single-flight, waiter cancellation and timeout isolation, source
failure/timeout cleanup, retry after cancelled fill, seeded expiry jitter
(peak 8), stale-while-revalidate behavior, hard expiry waiting, refresh
failure without freshness extension, and two independent subprocess fills
([1, 1]). Removing `asyncio.shield` causes the v2 experiment to fail, proving
the cancellation check is meaningful.

The tutorial explains cooperative cancellation, logical expiry time, and the
boundary that per-process maps do not deduplicate across processes. It does not
claim distributed locking or latency benchmarks. The final source is complete
and all task handles are collected.

No blocking findings. F04 is accepted for v0-v3.
