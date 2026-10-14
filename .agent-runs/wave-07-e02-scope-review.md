# E02 Original-Scope Review: REVISE

Scope: compare current code/tutorials/tests with `docs/roadmap.md:660` through
the E02 boundary at line 672. This is a source and evidence audit, not a new
PostgreSQL execution. No implementation, tutorial, or progress file changed.

## Blocking Scope Gaps

1. **v0 demonstrates a different failure.** Roadmap line 667 requires adding
   a required field and reproducing an old client's failed write. Current
   `labs/dataflows/schema_evolution/v0.py:15` renames name to full_name;
   lines 17-23 test SELECT name and UndefinedColumn. It never adds a required
   field or attempts an old-shape INSERT/UPDATE after migration. The tutorial
   title and prose explicitly teach rename/read failure, so this is a scope
   substitution, not merely an absent test. Keep the existing useful lesson
   as context if desired, but add the specified required-field write failure.
2. **Event schema compatibility is absent.** Roadmap line 672 requires event
   and table schema verification separately. The complete implementation and
   all four tutorial fences contain only PostgreSQL profiles-column migration,
   backfill, and read checks. No versioned event payload producer/consumer,
   old/new event compatibility matrix, or missing-field event rejection/default
   assertions exist in this module. SQL compatibility cannot establish event
   compatibility. Add independent event cases alongside the table cases.
3. **v1 does not verify its claimed old/new write matrix.**
   `v1.py:14-17` reads the old field, performs one new dual-write, then reads
   COALESCE. No old-client write runs after the new write, nor does the fallback
   branch run while full_name is NULL. The concrete missing sequence is:
   populate both columns with 'Ada Lovelace'; let an old writer update only
   name to 'Grace'; COALESCE(full_name,name) still returns 'Ada Lovelace'.
   Thus the described rolling-client protocol requires a declared policy and
   explicit compatibility cases; the current passing happy path is insufficient.
4. **v3 lacks behavior checks for final writes and retirement.**
   `v3.py:16` genuinely executes ALTER COLUMN full_name SET NOT NULL; the
   constraint is not imaginary. But `not_null=True` and cleanup_complete=True
   at line 26 are literals, while the only failure check is an old SELECT.
   Removing SET NOT NULL would leave those assertions green. Add explicit NULL
   and omitted-required-field writes expecting NotNullViolation/23502, a valid
   final-schema write/read, and a checked retirement/readiness condition before
   contraction. Verify legacy schema/transition artifacts are actually removed.

## Confirmed Current Evidence

- Independently checked all eight Python fences (common.py and vN.py per
  chapter): each exactly matches current source; all four checks passed.
- Source inspection confirms v0 rename/read failure, v1 nullable expansion,
  dual-write and COALESCE on a populated value, and v3 real NOT NULL DDL plus
  removal of the legacy column and rejection of its read.
- v2 includes fresh-process exits after commit (17) and before commit (19),
  atomic row/checkpoint writes, rollback assertions, resume, and preservation
  of a pre-existing new-client value. These are useful existing mechanisms.
- `.agent-runs/wave-03/reviews/e02-final.md` reports a historical live run of
  5 passed in 2.86s. That record explicitly describes rename/additive/backfill/
  contraction checks; it does not prove the missing roadmap behavior. This
  review did not rerun the stack or treat historical observations as new ones.

## Additional Evidence Limit

`v2.py:58` returns resume_batch=2 and repeat_batch=0 as constants. The worker
at lines 61-63 discards backfill's returned processed count, so successful
worker exits plus final state do not measure zero repeat work. Return and assert
the worker's observed counts. Also, common.reset drops only profiles while v2
creates schema_backfill_checkpoint without resetting it; a second whole v2
experiment on the same database will hit DuplicateTable. Distinguish repeatable
worker recovery from a repeatable experiment setup.

Decision: **REVISE / reopen full E02 scope acceptance**. Preserve the valid
rename/backfill evidence, but do not use it to accept required-field old-write
failure, an explicit rolling compatibility matrix, event-schema compatibility,
or final write rejection. Only this review artifact was added; no abstraction
or implementation cleanup was introduced.
