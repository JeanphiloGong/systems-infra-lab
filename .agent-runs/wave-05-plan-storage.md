# Wave 05 plan author evidence: S/P/T

The inventory against `docs/roadmap.md` found complete per-version plans for
S01-S07 and T01-T04. P01 and P02 also already had all required version plans.
The only missing files in the requested S/P/T scope were P03 v0-v4:

```text
tutorials/03-partitioning-scaling/03-migration/v0/plan.md
tutorials/03-partitioning-scaling/03-migration/v1/plan.md
tutorials/03-partitioning-scaling/03-migration/v2/plan.md
tutorials/03-partitioning-scaling/03-migration/v3/plan.md
tutorials/03-partitioning-scaling/03-migration/v4/plan.md
```

Each plan now states the real migration scenario, compressed model, invariants,
dependencies, Pressure/Naive/Break/Change/Check/Freeze/Still-lacks/Next chain,
complete checkpoint-fence requirement, isolated replay command, and explicit
deterministic-model boundary. The plans match the existing checkpoint behavior:
pause/copy, background-copy gap, idempotent tombstone delta replay, route barrier
and stale-route rejection, and restart/fencing.

Author verification:

```text
$ uv run python tests/partitioning/migration/replay_p03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok

$ uv run pytest tests/partitioning/migration -q
3 passed
```

The path audit found no missing version plans under the S01-S07 and T01-T04
tutorial directories. F01 `07-connections` and R01-R04 replication directories
were intentionally excluded because they are outside this S/P/T batch.
