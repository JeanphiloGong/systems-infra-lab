# Q02 v3 Repair Independent Review: REVISE

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## Live behavior replay

The repository PostgreSQL service was available at port 55432. The repaired
implementation passed the live regression suite:

```text
$ SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab' \
  uv run pytest tests/query/indexes/test_postgres.py -q
....                                                                     [100%]
4 passed in 3.85s
```

The full live replay passed v0-v3, including the repaired v3 checkpoint:

```text
$ SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab' \
  uv run python tests/query/indexes/replay_q02.py
v0 live replay ok
v1 live replay ok
v2 live replay ok
v3 live replay ok
```

The v3 metrics were:

```text
visible:  Index Only Scan, heap_fetches=0
updated:  Index Only Scan, heap_fetches=200
vacuumed: Index Only Scan, heap_fetches=0
```

The v3-only replay also passed with the same boundary, and the model tests
passed:

```text
$ uv run pytest tests/query/indexes/test_q02_indexes.py -q
2 passed in 0.02s
```

This independently confirms the explicit `VACUUM (FULL, ANALYZE)` rewrite
repairs the all-visible state on the observed PostgreSQL 16 service while
ordinary `VACUUM (ANALYZE)` alone did not.

## Fence parity finding

An all-version comparison of each tutorial `postgres.py` fence with the
current `labs/query/indexes/postgres.py` did not pass:

```text
v0 equal False
v1 equal False
v2 equal False
v3 equal True
```

The v0-v2 tutorials contain standalone, version-specific checkpoints whose
code is intentionally smaller than the current version-dispatching lab
module. v3 now matches the lab source exactly. Therefore the repaired v3
fence is synchronized, but v0-v2 are still not word-for-word parity with the
current lab file. This is relevant because the request called for v0-v3 fence
parity and the tutorial checkpoints are presented as the runnable source
artifacts.

## Decision

**REVISE for the requested v0-v3 parity scope.** Q02 v3 behavior and all live
replays pass, but the all-version fence parity check fails for v0-v2. Either
restore exact source parity for those checkpoints or explicitly document the
standalone historical checkpoint boundary and adjust the parity acceptance
contract before closing this review.

No implementation, tutorial, plan, progress, or index files were changed;
only this review artifact was added. No abstraction or cleanup was
introduced.
