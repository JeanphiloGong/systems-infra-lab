# Q03 PostgreSQL Scope Repair

Supersedes the former simulation-only acceptance. Source: `labs/query/planner/postgres.py`; complete version-specific tutorial checkpoints under `tutorials/04-query/03-planner/v0-v3`. Old Python model remains explanatory only. Each experiment creates a unique q03_ schema, uses real PostgreSQL queries and EXPLAIN ANALYZE BUFFERS SETTINGS JSON, then removes that schema in finally.

## Verification

On the existing isolated PostgreSQL 16.14 service, with SYSTEMS_LAB_DATABASE_URL exported:

```text
uv run pytest tests/query/planner -q
7 passed in 5.94s (4 PostgreSQL cases, 3 earlier explanatory model tests)

uv run python tests/query/planner/replay_q03.py
v0 live replay ok
v1 live replay ok
v2 live replay ok
v3 live replay ok
```

Replay extracts only each version's printed standalone postgres.py and runs it in a fresh directory/interpreter. No future-version branches are printed. No current worktree planner module is imported. The DSN is required; missing database setup is not reported as a pass.

## Measured Plans

| Experiment | Plan | Estimate | Actual | Other measurements |
| --- | --- | ---: | ---: | --- |
| v0 20-row table | Seq Scan | 1 | 1 | 1 buffer hit, 0.022 ms |
| v0 100,000-row table | Bitmap Heap/Index Scan | 100 | 100 | 100 hits + 2 reads, 0.304 ms |
| v1 stale distribution | Bitmap Heap/Index Scan | 190 | 90010 | 2900 hits, 26.531 ms |
| v1 after ANALYZE | Seq Scan | 89853 | 90010 | 5758 hits, 29.585 ms |
| v2 rare independent | Seq Scan | 2 | 500 | correlated equality predicates |
| v2 rare extended | Seq Scan | 500 | 500 | dependencies+MCV stats |
| v2 hot independent | Seq Scan | 25000 | 50000 | skew plus correlation |
| v2 hot extended | Seq Scan | 50000 | 50000 | same predicates/data |
| v3 nested join | Nested Loop + Memoize + Index Only Scan | 40000 | 40000 | 7482 hits, inner scan loops 2000, Memoize 204 kB, 34.523 ms |
| v3 hash join | Hash Join + Hash + Seq Scans | 40000 | 40000 | 1491 hits, hash 87 kB/1 batch, 20.548 ms |
| v3 64kB sort | Sort external merge | 40000 | 40000 | disk 10792 kB, temp reads 5376 blocks/writes 5656 blocks, 206.341 ms |
| v3 64MB sort | Sort quicksort | 40000 | 40000 | memory 12787 kB, temp reads/writes zero, 130.220 ms |

All full plans are returned by the source and printed by standalone tutorial commands. The replay projection retains measured operator rows, loops, elapsed time, hash batches, memory, and spill. PostgreSQL block_size is 8192 bytes. Temporary block counts are cumulative database-layer I/O, not peak space or guaranteed hardware I/O.

Result checks verify reference output at both table sizes, unchanged query results across ANALYZE/statistics changes, identical join pairs for nested/hash strategies, and identical ordered wide rows for both sort settings. Assertions require observed plan categories, improved estimate error, and actual positive-to-zero temp I/O; they do not assert fixed timings or speedups.

## Limits and Choices

v0 changes table scale under the same indexed predicate. v1 disables autovacuum only on its temporary table and introduces a hotspot before manual ANALYZE; the table's physical size may still be known while column distributions remain stale. The refreshed plan was slower in this warm-cache observation, explicitly recorded rather than hidden.

v2 uses high statistics targets for a full enough sample of the small fixture; dependencies+MCV apply to correlated same-table equalities, not arbitrary correlations. v3 deliberately discourages alternate join types via session enable_* controls for a diagnostic comparison; it does not claim those forced alternatives are an automatic optimizer decision or production tuning advice. Sort work_mem is per operation, not total backend RSS.

Core PostgreSQL EXPLAIN does not expose actual CPU milliseconds separately. The artifacts honestly report cpu_tuple_cost/cpu_index_tuple_cost/cpu_operator_cost as planner assumptions, actual rows/loops as work evidence, and execution time as elapsed time. No fabricated CPU metric, spill bytes, or simulated plan substitutes for measured database behavior.

New permanent code is a direct PostgreSQL experiment driver and its parsing helpers. There is no compatibility layer or temporary implementation. Every run drops its unique schema on normal success or exception. Independent review remains pending.
