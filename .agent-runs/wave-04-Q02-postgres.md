# Q02 PostgreSQL Scope Repair

Final review repairs verified: each tutorial now prints a version-specific complete checkpoint with no future-version dispatch branches. v1 uses identical projection/order (`SELECT id, amount FROM orders WHERE user_id=... ORDER BY id`) and varies only user_id=42 versus user_id=0. Full result rows are asserted in both cases. PostgreSQL still chose Sort/Index Scan (100 rows, 102 buffers) versus Sort/Seq Scan (90,000 rows, 3125 buffers). Live tests: 6 passed in 2.80s; all four extracted live replays passed again. Earlier references to common-value plain Seq Scan mean its scan node; the controlled query now also has Sort.

This evidence supersedes the earlier simulation-only Q02 acceptance. The original roadmap requires PostgreSQL plans, actual reads, Index Only Scan, Heap Fetches, and VACUUM. These are now exercised against PostgreSQL 16.14 (server_version 160014).

Source: `labs/query/indexes/postgres.py`. Each version uses a unique disposable schema with 100,000 real rows. `finally` drops only that schema. Autovacuum is disabled on that disposable table, and parallel query is disabled for readable plans. No scan-selection flags force index use. Full EXPLAIN ANALYZE BUFFERS JSON is returned alongside metrics.

All four tutorial fences contain the complete live experiment source. Replay extracts that code into an empty directory, requires SYSTEMS_LAB_DATABASE_URL, and runs a fresh interpreter with PYTHONPATH pointing only to the temporary directory. The old model.py is explanatory and provides no PostgreSQL acceptance evidence.

Commands, with the existing isolated DSN exported:

```text
uv run pytest tests/query/indexes -q
6 passed in 5.21s (4 real PostgreSQL cases, 2 older explanatory model tests)

uv run python tests/query/indexes/replay_q02.py
v0 live replay ok
v1 live replay ok
v2 live replay ok
v3 live replay ok
```

Measured replay evidence:

| Version/case | Actual plan | Actual output rows | Shared buffer accesses | Heap fetches |
| --- | --- | ---: | ---: | ---: |
| v0 baseline | Sort / Seq Scan | 100 | 3125 | not applicable |
| v1 selective | Sort / Index Scan | 100 | 102 | not an IOS counter |
| v1 common | Seq Scan | 90000 | 3125 | not applicable |
| v2 user,time | Limit / backward Index Scan | 20 | 22 | not applicable |
| v2 time,user | Limit / backward Index Scan | 20 | 34 | not applicable |
| v3 before UPDATE | Index Only Scan | 100 | 4 | 0 |
| v3 after UPDATE | Index Only Scan | 100 | 204 | 200 |
| v3 after VACUUM | Index Only Scan | 100 | 4 | 0 |

The v0 child scan removes 99,900 rows by filtering. v1 compares skewed selectivities without forcing access methods. v2 executes the identical user/time-range/descending-order/limit SQL with each column order and checks complete result equality against the unindexed baseline. v3 verifies amounts change by exactly one and remain unchanged through VACUUM.

Root shared hit/read counts are inclusive; they are not summed again over children. Shared reads can be served from OS cache and are not physical-device I/O. Local execution times are reported but not asserted as performance guarantees. Sampling causes row estimates to vary; assertions check behavior rather than exact estimates. This evidence is author verification; independent review is pending.
