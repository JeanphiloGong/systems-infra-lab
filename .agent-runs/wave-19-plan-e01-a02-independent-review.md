# Wave-19 independent plan review: E01/A02

## Findings

No blocking plan-field or contract inconsistency found. All nine plans were
read individually. Their explicit fields preserve existing scenarios, source
targets, acceptance observations, and external dependencies. These are build
plans; this verdict does not evaluate tutorial prose style or certify live CDC.

## Per-version assessment

| Plan | Specific contract checked | Result |
| --- | --- | --- |
| E01 v0 | Source row versus empty projection exposes divergence | Plan PASS |
| E01 v1 | Real numeric LSN ordering, transaction boundaries, three unique data events | Plan PASS |
| E01 v2 | Snapshot cut and tail produce exact projection and cursor ordering | Plan PASS |
| E01 v3 | Initial snapshot survives pre-commit crash; projection/checkpoint commit before source acknowledgment | Plan PASS |
| E01 v4 | More than 20,000 events, retained WAL, advancing confirmed position | Plan PASS |
| A02 v0 | Full WAL read cost and rejection of missing/corrupt segments | PASS |
| A02 v1 | Snapshot plus five-file tail; 100+5 test distinct from 10+5 fence probe | PASS |
| A02 v2 | Validate/publish before reclaim; crash boundaries preserve position 5 | PASS |
| A02 v3 | Two retained generations, 15-transaction fallback, rotation exits 71-75 | PASS |

E01 v3 was checked against the worker and experiment: the initial snapshot is
published before the tested incremental transaction; a pre-commit crash leaves
that snapshot intact and no checkpoint. The plan correctly limits its atomicity
claim to incremental projection/checkpoint writes and does not claim exactly-once
external effects. A02 v1's two workloads and v3's fallback/rotation assertions
agree with the existing experiment and replay checks.

## Independent verification

- `uv run pytest tests/recovery/checkpoint -q`: 16 passed in 10.17s.
- `uv run python tests/recovery/checkpoint/replay_a02.py`: v1-v3 passed;
  outputs include positions 15, 5, and 25 with the documented balances.
- Called E01 replay helper `extract` separately for each v0-v4 in temporary
  directories: all five complete fence lists and exact source comparisons passed.
- Read `tests/dataflows/cdc/test_e01_replay.py` and E01 v3 source to compare
  observations and crash/ack ordering. No live PostgreSQL tests were rerun.
  Author-reported 7 failures/1 pass reflect missing DSN or refused dedicated
  endpoint; they are not independent runtime passes.

## Verdict

PASS for this plan-expression revision. Live E01 behavior remains unverified
in this wave and requires its dedicated PostgreSQL environment. A02 evidence
covers local file/process crashes, not power loss or cross-host recovery.
This review changed only its evidence file, added no code abstraction, and
performed no implementation cleanup.
