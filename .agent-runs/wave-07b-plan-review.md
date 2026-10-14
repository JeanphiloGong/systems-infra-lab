# Wave 07b Independent Plan Review

## D02/Q01: PASS for Plan Fidelity

Read all nine version plans and compared each with its current tutorial
checkpoint. Independently executed the exact bash extraction block from every
plan from the repository root. All nine returned exit 0; each ran its own
checkpoint.py in an automatically cleaned temporary directory.

| Version | Independently observed result |
| --- | --- |
| D02 v0 | winner=b, contenders=2; code asserts one winner, a also valid |
| D02 v1 | old_owner_paused=True, new_owner=b, overlap_risk=True |
| D02 v2 | stale_rejected=True, token=2 |
| D02 v3 | stale_renew_rejected=True, current_owner=b, token=2, expires_at=5 |
| D02 v4 | availability=unknown, do not write, resource token=2/value=new |
| Q01 v0 | inconsistent_rows=2 |
| Q01 v1 | join=A. Lovelace/Widget/12, foreign_key_rejected=True |
| Q01 v2 | read_joins=0, view_update_writes=1, stale_window=True |
| Q01 v3 | normalized_read_ops=2, denormalized_read_ops=1, extra_write_ops=1, stale_read_model=True, snapshot_price=12 |

Each plan has a concrete pressure, prior gap, code-matched mechanism, check,
freeze, limitation, and next step. It explicitly distinguishes single-version
extraction from the all-version replay. Limitations are accurately disclosed:
D02 v3 has renewal but no release; Q01 v1 inserts an invalid dictionary row
before asserting and is not a database rollback; Q01 v3's maintenance budget
is declared rather than an executed write. D02 v1/v4 are scripted logical
scenarios, not distributed service observations. This accepts the plans as
faithful descriptions of their current checkpoints, not full original-scope
implementation acceptance or a closure of thin tutorial prose findings.

## E02 Module Plan: REVISE, Two Missing Specifics

The new module plan substantially carries forward the scope review: it
separates required-field DDL failure from old INSERT failure, requires a
table compatibility matrix and an independent event producer/consumer matrix,
requires observed worker counts, documents cursor/writer assumptions, and
requires final constraint checks, invalid writes and transition-state cleanup.
Its live commands match the existing isolated PostgreSQL replay entry point.

Before treating it as a complete repair contract, explicitly add:

1. **New write followed by old update followed by new read, on the same row.**
   Merely checking old-write/new-read on an empty full_name and
   new-write/old-read separately misses the identified stale COALESCE case.
   Specify the expected authoritative value and choose the temporary
   synchronization or old-update restriction policy. The plan currently
   prescribes dual-write plus COALESCE without resolving that conflict.
2. **Repeat the entire v2 experiment on the same isolated database.** The
   current common.reset leaves schema_backfill_checkpoint behind, so the
   second setup fails at CREATE TABLE. The plan requires repeated workers,
   but not setup reset of both tables or a second full extracted experiment.
   Add this acceptance check separately from worker recovery/idempotency.

The E02 implementation remains reopened; approving a repaired plan would not
close its runtime gaps. Only this review record was added. No plan, source,
tutorial, progress, or index was changed; no abstraction or implementation
cleanup was introduced.

## E02 Plan Follow-up: PASS as Repair Contract

Re-read root's updated module plan. It now requires the complete same-row
new-write/old-update/new-read trace and names name as the authoritative field
through the migration window. New readers use name during that window; final
sync and retirement of old writers precede switching to full_name. Thus the
earlier COALESCE sentence should be read as the legacy-row example, not the
active mixed-writer protocol. The implementation and tutorial must preserve
this distinction and demonstrate the stale-COALESCE negative case.

It also now explicitly resets both profiles and schema_backfill_checkpoint
at experiment initialization, preserves checkpoints during worker restarts,
and requires two successful full v2 runs on the same database. Both requested
repair-plan specifics are addressed. E02 runtime scope remains REVISE pending
implementation and independent replay; no runtime acceptance was added.
