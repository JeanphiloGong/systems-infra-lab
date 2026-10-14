# Q04 Author Evidence

Original roadmap target used: labs/query/derived. Chinese version-specific tutorials: tutorials/04-query/04-derived/v0-v4. Tests and strict extracted replay: tests/query/derived. No other modules/progress ledgers changed.

## Live Verification

Against the existing isolated PostgreSQL 16 service, with SYSTEMS_LAB_DATABASE_URL exported:

```text
uv run pytest tests/query/derived -q
7 passed in 2.11s

uv run python tests/query/derived/replay_q04.py
v0 live replay ok
v1 live replay ok
v2 live replay ok
v3 live replay ok
v4 live replay ok
```

Observed v0 aggregation returned 30 daily rows, each 10,000, with 163 shared hits per execution. v1 source aggregate used 163 hits while materialized-view scan used 1; after source INSERT the source was 300,050 while view remained 300,000, until REFRESH.

v2 missing unique index produced SQLSTATE 55000; unpopulated view with unique index produced 0A000. A real open reader transaction blocked ordinary refresh for ~0.201 seconds until lock_timeout; concurrent refresh succeeded with that reader transaction still open. Conversely, ordinary refresh inside an uncommitted transaction blocked another connection's SELECT; releasing the transaction restored reads.

v3 TTL=5 logical seconds: two source loads and two hits, old read at 4.999 and fresh read exactly at 5. Separate tests cover loader failure and nonpositive TTL.

v4 uses Event-coordinated actual PostgreSQL reads/writes on separate connections. Old read pauses before fill; writer commits then invalidates. Naive fill returns 300,000, stays stale before TTL, and returns 300,050 at expiry. Epoch guard rejects one old fill, retries the database, and returns 300,050. Observed stale-window boundaries in the controlled logical schedule: 5 seconds naive versus zero after guarded retry. A separate commit-at-1/invalidate-at-2 experiment observes an explicit 1-second residual stale window, so the guide does not claim strong consistency.

Replay writes all checkpoint fences (common.py, the version module, cache.py where used) to temporary directories, overrides PYTHONPATH, and runs a fresh interpreter there. It imports no working-tree source. Every experiment creates and cleans only its unique q04_ schema.

## Limits and Cleanup

Buffer metrics are actual PostgreSQL-layer reads/hits, not physical disk operations. Cache TTL/window times use a deterministic monotonic logical clock; database lock waits use perf_counter wall time. Epoch is single-process and requires cooperative invalidation; it is not a distributed version service. Crash-lost invalidations, external writers, long snapshots, and continuous invalidation/starvation are explained as residual limitations. Unbounded repeated concurrent misses are not presented as single-flight cache coalescing.

Permanent abstraction: one single-key Cache for the real cache-aside experiments; common database setup centralizes unique-schema lifecycle. No adapters or compatibility layers were added. Schemas/connections/threads are cleaned by finally/context managers. Independent review pending; no acceptance claim and no commits.
