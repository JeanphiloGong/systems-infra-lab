# Q04 independent original-scope review

Verdict: PASS against `docs/roadmap.md:532` within the explicitly bounded PostgreSQL/cache model. No blocking findings.

## Actual verification

With the isolated PostgreSQL DSN, actually ran:

- `uv run pytest tests/query/derived -q`: **7 passed in 2.06s**, including all five live PostgreSQL/cache cases and two cache boundary tests.
- `uv run python tests/query/derived/replay_q04.py`: **v0-v4 live replay all passed** against PostgreSQL 16.14. Replay extracted every checkpoint to temporary directories, set PYTHONPATH there, and ran a fresh interpreter; it did not import worktree implementations. Independently checked all **12 printed Python fences** byte-exact against their source files.

## Scope evidence

- v0 executes the real 30,000-row daily aggregation twice. Both results are the explicit 30-day/10,000 reference, and EXPLAIN ANALYZE BUFFERS reports 163 shared hits per aggregation.
- v1 creates a real materialized view, inserts source data, and observes source total300,050 while the view remains300,000. Source aggregation measures163 hits; direct view read measures1. Explicit REFRESH changes the view to300,050. The text distinguishes read cost from refresh/maintenance cost.
- v2 uses two real PostgreSQL connections and an open reader transaction. Without a unique index, concurrent refresh returns SQLSTATE55000; an unpopulated view with an index returns0A000. Ordinary refresh waits for the reader until the ~200ms lock timeout; populated concurrent refresh succeeds while that reader remains open. An ordinary refresh held in a writer transaction blocks another SELECT until commit. Results after commit are300,050.
- v3 uses an injected logical clock with exact boundaries: TTL5, value is old at4.999 and reloads at5. Failed loaders propagate and are not cached; nonpositive TTL is rejected. Two source loads and two cache hits are observed.
- v4 coordinates separate PostgreSQL reader/writer connections with Events. The reader captures300,000, writer commits300,050 then invalidates, and the naive fill stores/returns the old value until TTL expiry. Epoch guard rejects that fill, retries the database and returns300,050. A separate commit-at1/invalidate-at2 schedule observes a one-second stale window. Results are correctly described as controlled logical schedules, not production latency or strong consistency.

## Boundaries and measurements

The cache lock/epoch is single-process and cooperative. External writes, crash-lost invalidation, delayed invalidation, long snapshots, repeated invalidation/starvation and cross-process coordination are not covered; the tutorials state these limits. No single-flight claim is made. Database buffer counts are PostgreSQL-layer accesses, not physical-device I/O. Lock wait uses wall-clock measurement; TTL/stale windows use a deterministic logical clock.

Successful materialized-view refresh duration/work is not separately measured as a benchmark; the evidence measures source/view read plans, refresh blocking and refresh correctness. The roadmap requires comparing refresh behavior and read blocking, which is satisfied by these lock/compatibility experiments, but readers should not infer a refresh cost number from the read-plan metrics.

Review artifact only; no implementation abstraction or source cleanup added.
