# A01 Original-Scope Review: REVISE

Independent read-only comparison of roadmap lines 599-612, the new module
plan, all five version implementations/tutorials, common.py, and extraction
tests. No database started; no new runtime result is claimed.

## Confirmed Scope Gaps

1. **v0 restores into its source database and does not check constraints.**
   Roadmap line 606 explicitly requires an independent restore database and
   table/row/constraint checks. `labs/recovery/backup/v0.py` drops accounts
   on the seed connection and invokes psql with that same connection DSN.
   It verifies two exact rows, but never tests duplicate-key/NULL rejection
   or inspects restored constraints. This proves a logical round trip, not
   the specified independent recovery exercise. Restore to a separate
   temporary database; verify data, schema and constraints while retaining
   the source's contents.
2. **v2 substitutes logical-dump corruption for physical backup/continuity.**
   Roadmap line 608 requires base backup, WAL archiving and archive
   continuity. `v2.py` only truncates a custom logical dump and expects an
   exception from pg_restore. Physical backup is actually invoked in v3/v4.
   `common.wait_archive` lines 45-55 checks existence and size of one selected
   segment; it does not enumerate and validate the required interval from
   the backup's recovery start through the chosen target/timeline. A successful
   v3 recovery proves its particular chain was usable, not the missing v2
   continuity experiment. Implement the v2 checkpoint and its negative gap
   check, preserving the logical-corruption lesson in the fault section.
3. **v4 has no measured recovery duration or loss window.** Roadmap line 610
   requires both. Its result contains only missing-archive/failure flags and
   an error excerpt. common.py uses monotonic deadlines to bound polling,
   but returns neither elapsed time nor committed-operation/time boundaries.
   timeout=5 is a configured budget, not an observed recovery duration.
   Record elapsed attempt time and a successful recovery duration with defined
   start/end events; compare acknowledged source/target operations and their
   times to describe the omitted data window. A failed recovery has no valid
   recovered-data RPO; report failure separately rather than inventing one.

v1 already demonstrates the requested post-backup-row exclusion, but still
uses pg_restore --clean against the same source DSN. The new module plan's
independent-target carry-forward is appropriate for this tutorial progression.

## Evidence Preserved

The historical independent run recorded in
`.agent-runs/wave-04-A01-review-final.md` remains valid evidence: root started
the isolated stack, observed **6 passed in 19.15s**, and cleaned with down -v.
That result establishes the actual checks run then:

- Logical round trip and exclusion of the later inserted row.
- A truncated logical dump causes a restore exception.
- v3 performs a real pg_basebackup, waits for archived WAL, starts a distinct
  PostgreSQL recovery container, waits for target pause, restores 1:100,2:100
  while source is 1:100,3:300, and therefore meets the core PITR requirement.
- v4 removes a WAL segment from a private archive copy and requires the exact
  target-not-reached error. The original archive remains intact.

The earlier full-module PASS overreached that evidence. This review supersedes
full original-scope acceptance, not those observed successful PITR checks.

## Module Plan Assessment

The new module plan correctly identifies independent restore/constraint
validation, physical-backup version ordering, continuity and timing/loss
measurements as unfinished work. It preserves working PITR behavior and assigns
checks to the extracted replay path. It is a suitable repair contract, with
the timing distinction above made explicit during implementation. None of its
future assertions count as current runtime evidence.

Only this review artifact was added. No progress/index, source, tutorial,
plan, abstraction or implementation cleanup was changed.
