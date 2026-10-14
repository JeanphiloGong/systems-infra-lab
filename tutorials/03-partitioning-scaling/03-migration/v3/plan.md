# P03 v3 Plan: Barrier and stale-route rejection

## Reader Goal

Move integer-keyed records from owner `a` to owners `a,b` while preserving confirmed writes and rejecting stale routing decisions.

## Real Scenario and Compressed Model

A service changes its shard layout while clients continue to use the old route. The model contains records, an owner map, a monotonically increasing write sequence, a delta log, a route version, and a fencing token. It is an in-memory teaching model; it does not claim zero-downtime production migration.

## Invariants and Dependencies

- Every read through the current route returns the latest accepted value, including `None` tombstones.
- A confirmed sequence is copied or replayed before the route version can advance.
- A request carrying an old route version or fence token is rejected.
- This version depends on the previous version's `Migration` state and `checkpoint.py` fence. Prerequisite: P01 routing concepts.

## Tutorial Increment

1. **Pressure:** Cutting over before the last delta is applied loses confirmed writes; old clients can write the old owner.
2. **Naive baseline:** Flip the route table immediately after copying.
3. **Break:** The baseline cannot distinguish copied history from writes that arrived during migration.
4. **Change:** Choose a sequence barrier, replay through it, increment route version, and reject an old route version.
5. **Check:** Replay proves route version 2, all six values preserved, and stale read rejected.
6. **Freeze:** Keep the complete `checkpoint.py` fence and its printed result as the reproducible checkpoint.
7. **Still lacks:** A process crash during migration can lose phase and fencing state.
8. **Next:** v4 persists state and resumes with a fencing token.

## Complete Checkpoint and Replay

The tutorial must include the complete `checkpoint.py` source fence, with no imports supplied from the repository. Extract the fence into an empty directory and run:

```bash
uv run python tests/partitioning/migration/replay_p03.py
uv run pytest tests/partitioning/migration -q
```

Acceptance is version-specific: the replay executes v3 from the extracted fence, and the test suite preserves the migration invariants for pause/copy, delta handling, routing barriers, and fencing. Do not replace the printed observation with a hardcoded label.

## Boundary

This checkpoint uses deterministic dictionaries, integer sequences, and process-local JSON state. It does not measure network bandwidth, disk durability, concurrent writers, or a production resharding controller.

