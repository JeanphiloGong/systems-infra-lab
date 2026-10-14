# E01/A02 Plan Batch Independent Review: PASS

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## E01 CDC

The author run lacked the dedicated logical-replication service, so its
failures were environment-limited. I independently started the isolated
stack and reran the suite:

```text
$ docker compose -f infra/e01.compose.yaml up -d --wait
$ E01_DATABASE_URL='postgresql://e01:e01_local_only@127.0.0.1:55450/e01' \
  uv run pytest tests/dataflows/cdc -q
........                                                                 [100%]
8 passed in 3.84s
```

This covers all five extracted v0-v4 real PostgreSQL logical-replication
checkpoints plus decoder-value and snapshot-cut behavior. The tests verify
source/projection divergence, ordered decoded events and LSNs, snapshot plus
tail convergence, transactional checkpoint/crash recovery, and retained WAL
while a consumer is paused.

An independent fence/source comparison found both `common.py` and each v0-v4
source fence exactly matched their referenced `labs/dataflows/cdc` files (10
checks). The revised plans identify the source scenario, pressure/change,
observable checkpoint, external PostgreSQL requirement, and next version
boundary for each version. The dedicated stack was removed after the run.

## A02 checkpoint recovery

The complete A02 test suite passed:

```text
$ uv run pytest tests/recovery/checkpoint -q
........                                                                 [100%]
16 passed in 9.48s
```

The extracted tutorial replay also passed:

```text
$ uv run python tests/recovery/checkpoint/replay_a02.py
A02 tutorial v1-v3 replay ok: [
  "({'alice': 85, 'bob': 115}, 15)",
  "0 ({'alice': 95, 'bob': 105}, 5)",
  "({'alice': 75, 'bob': 125}, 25)"
]
```

The replay compares all three checkpoint fences (`framing.py`,
`baseline.py`, and `store.py`) with their repository sources before running
the v1-v3 recovery probes. An independent comparison found all A02 v0-v3
fences match their source files (12 checks). The plans describe full replay,
snapshot tail recovery, publication/reclaim crash boundaries, retained
generations, and fallback behavior with concrete assertions and limits.

## Decision

**PASS for E01 and A02.** E01's initial unavailable-service result is
superseded by the independent live run; it is retained here as an environment
context, not counted as a pass. A02 is self-contained and passed its full
tests and replay. The E01 Compose stack was cleaned with
`docker compose -f infra/e01.compose.yaml down`; no implementation,
tutorial, plan, progress, or index files were changed. Only this review
artifact was added; no abstraction or cleanup was introduced beyond service
cleanup.
