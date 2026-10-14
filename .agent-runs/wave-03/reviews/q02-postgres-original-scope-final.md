# Q02 original PostgreSQL scope review

Verdict: PASS for the repaired original PostgreSQL experiment scope at `docs/roadmap.md:508`. This supersedes the earlier simulation-only Q02 verdict and resolves the Q02 portion of `q02-q03-original-scope-reopened.md`. Q03 remains separately pending.

## Actually executed

With `SYSTEMS_LAB_DATABASE_URL=postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab`:

- `uv run pytest tests/query/indexes -q`: **6 passed in 2.96s**. Four cases run live PostgreSQL, two are explanatory Python model tests.
- `uv run python tests/query/indexes/replay_q02.py`: **v0-v3 live replay all passed**, reporting server version **160014**. The script extracts the printed Python fence into an empty temporary directory and executes a fresh interpreter there with temporary-directory PYTHONPATH.
- Independently extracted each of the four Python fences using sed and compared it with `labs/query/indexes/postgres.py` using cmp: all four byte-exact. The replay script itself does not assert this equality, so that check is separate evidence.

## Observed original-scope behavior

| Checkpoint | Actual execution evidence |
| --- | --- |
| v0 | Sort / Seq Scan, 100 returned rows, 99,900 filtered rows checked by the live pytest assertion, 3,125 root buffer accesses |
| v1 selective | Sort / Index Scan, 100 rows, 102 buffer accesses; full returned tuples equal pre-index result |
| v1 common | Seq Scan, 90,000 rows, 3,125 buffer accesses |
| v2 user,time | Limit / Index Scan, 20 rows, 22 buffer accesses |
| v2 time,user | Limit / Index Scan, 20 rows, 34 buffer accesses |
| v3 before update | Index Only Scan, 100 rows, 0 Heap Fetches |
| v3 after update | Index Only Scan, 100 rows, 200 Heap Fetches |
| v3 after VACUUM | Index Only Scan, 100 rows, 0 Heap Fetches |

v2 compares the identical equality/range/descending-order/limit query and complete results against its unindexed baseline. v3 checks each amount increases by one and VACUUM preserves the changed results. Measurements come from EXPLAIN ANALYZE BUFFERS JSON, not assigned counters. The full plan remains available, alongside root metrics. Root buffer counts are not double-counted over children; buffer reads are correctly distinguished from physical-device reads in the prose.

## Boundaries and follow-up quality notes

Only a unique disposable schema is dropped; autovacuum is disabled only on its table. The fixture disables parallel query for clarity but does not force index selection. Exact node choices and comparative buffer assertions are verified on the pinned PostgreSQL 16 fixture, not promised across all settings/releases. Runs are warm-cache observations, not cold-device benchmarks.

The selective and common v1 queries also differ in projection/order, so the result demonstrates these concrete workloads rather than isolating selectivity as the sole causal variable. The prose should not claim a controlled single-variable comparison.

Each tutorial currently prints the same complete four-experiment driver, including future branches. This makes replay self-contained but is weaker incremental teaching than growing only the current checkpoint. The scope repair establishes real database behavior; it does not establish ideal from-scratch tutorial progression. Splitting version-specific bodies remains an editorial improvement.

Review artifact only. No implementation abstraction added; no source cleanup performed.
