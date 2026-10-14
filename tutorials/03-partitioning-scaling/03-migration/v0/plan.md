# P03 v0 Plan: Pause-and-copy baseline

## Reader Goal

Move integer-keyed records from owner `a` to owners `a,b` while preserving confirmed writes and rejecting stale routing decisions.

## Real Scenario and Compressed Model

A service changes its shard layout while clients continue to use the old route. The model contains records, an owner map, a monotonically increasing write sequence, a delta log, a route version, and a fencing token. It is an in-memory teaching model; it does not claim zero-downtime production migration.

## Invariants and Dependencies

- Every read through the current route returns the latest accepted value, including `None` tombstones.
- A confirmed sequence is copied or replayed before the route version can advance.
- A request carrying an old route version or fence token is rejected.
- This is the initial migration model. Its prerequisite is P01 routing concepts; the tutorial supplies the complete `Migration` and checkpoint implementation locally.

## Tutorial Increment

1. **Pressure:** Writes during a live move can diverge source and target.
2. **Naive baseline:** Copy while serving writes and trust the final row count.
3. **Break:** The baseline cannot distinguish copied history from writes that arrived during migration.
4. **Change:** Pause writes, copy every key to the target owner map, and reject a write during the pause.
5. **Check:** Run the fenced checkpoint; all eight reads match, the write is rejected, and rows=8 is printed.
6. **Freeze:** Keep the complete `checkpoint.py` fence and its printed result as the reproducible checkpoint.
7. **Still lacks:** The service has downtime and no incremental catch-up.
8. **Next:** v1 copies while writes continue so the missing delta becomes visible.

## Complete Checkpoint and Replay

The tutorial must include the complete `checkpoint.py` source fence, with no imports supplied from the repository. Extract the fence into an empty directory and run:

```bash
uv run python tests/partitioning/migration/replay_p03.py
uv run pytest tests/partitioning/migration -q
```

Acceptance is version-specific: the replay executes v0 from the extracted fence, and the test suite preserves the migration invariants for pause/copy, delta handling, routing barriers, and fencing. Do not replace the printed observation with a hardcoded label.

## Boundary

This checkpoint uses deterministic dictionaries, integer sequences, and process-local JSON state. It does not measure network bandwidth, disk durability, concurrent writers, or a production resharding controller.

