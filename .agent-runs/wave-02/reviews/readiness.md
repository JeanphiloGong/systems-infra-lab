# Wave 02 review readiness

Scope: S02 B+Tree/page index and T03 optimistic/pessimistic locking and
deadlock. No tutorial checkpoint is accepted by this file.

## Dependency checks

- S02 v0-v4 are in-memory/index-structure increments; disk persistence begins
  only at the roadmap's S02 v5 and requires S03 persistence knowledge.
- S02 invariants must include ordered keys, leaf depth, parent ranges, and
  lookup preservation across splits. Duplicate-key replacement semantics must
  be explicit.
- T03 starts from T02 concurrency knowledge. Database experiments must use
  barriers or deterministic transaction sequencing, not sleep timing.
- T03 optimistic updates must check affected-row counts; stale writers must be
  visibly rejected rather than reported successful. Pessimistic-lock examples
  must state lock scope, wait behavior, and transaction ownership.
- Deadlock experiments must demonstrate a real database-aborted transaction
  and distinguish that error from a client timeout. Fixed lock ordering should
  be tested as the scoped prevention mechanism.
- Lock Escalation is a separate teaching simulation in the roadmap because
  PostgreSQL does not perform SQL Server-style row-lock escalation; no tutorial
  may imply the simulation is PostgreSQL behavior.

## Acceptance protocol

For each version, inspect the plan and tutorial for pressure, prior baseline,
complete checkpoint, exact file target, and meaningful check. Extract and run
the printed complete checkpoint in a temporary directory where possible, then
run the author's focused tests. Final-source tests alone do not prove tutorial
continuity. Record document hashes and findings in this directory; require
author fixes followed by independent replay before acceptance.

## Verdict

ready; waiting for S02/T03 v0 artifacts.
