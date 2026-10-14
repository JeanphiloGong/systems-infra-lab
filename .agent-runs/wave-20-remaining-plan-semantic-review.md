# Wave-20 remaining plan semantic review

## Findings

1. **REVISE: D04 v1 promises a restart/failure observation its checkpoint does
   not produce.** `tutorials/07-coordination/04-saga/v1/plan.md:3` describes a
   process exit and new process; line 7 expects a failed/resumable status.
   The complete tutorial fence runs `Saga(':memory:')` once and prints
   `['reserve', 'charge']` plus `[('reserve', 'done'), ('charge', 'done')]`.
   `tests/coordination/saga/test_d04.py:test_v1_restart_does_not_repeat_done_step`
   closes and reopens a file-backed connection in the same process, proving
   completed-marker persistence, not process-crash recovery. The replay test
   checks fence parity and successful exit only. Align the plan to these two
   actual checks and state the unresolved effect-before-done-marker crash
   window: `effect()` precedes the durable `done` update. Do not imply arbitrary
   completed external effects cannot repeat after a crash.

2. **REVISE: D04 v2 reverses the compensation order incorrectly.**
   `tutorials/07-coordination/04-saga/v2/plan.md:3` and line 7 require release
   before refund. The forward steps are reserve then charge, so reverse order
   is refund then release. The tutorial calls compensation positions 2 then 1
   and prints `reserved, charged, refunded, released`;
   `test_v2_reverse_compensation_is_idempotent` asserts
   `reserve, charge, refund, release`. Correct the plan's exact observation
   and note that the caller supplies reverse order; the journal does not
   automatically schedule that order.

3. **REVISE: P03 v0 depends on a nonexistent previous version.**
   `tutorials/03-partitioning-scaling/03-migration/v0/plan.md`, Invariants and
   Dependencies, requires the previous version's `Migration` and checkpoint.
   This is the initial checkpoint and its tutorial supplies the full class.
   Replace that dependency with P01 routing knowledge and construction of the
   initial local model. The pause/copy result and downtime limitation are
   otherwise concrete.

4. **REVISE: P03 v2 introduces reordered delivery as pressure without bounding
   what its replay actually guarantees.**
   `tutorials/03-partitioning-scaling/03-migration/v2/plan.md`, Tutorial
   Increment item 1, includes reordered messages. The tutorial's
   `apply_delta` at lines 62-70 iterates the existing append-ordered list and
   deduplicates sequence IDs; it does not sort, reject, or version-check an
   out-of-order overwrite. Existing checks cover ordered updates, tombstones,
   and repeating the same log, not reordered delivery. Narrow the pressure
   and limit to ordered replay with duplicates, leaving network reordering
   deferred. The repeated generic Break sentence is not itself a failure;
   the missing ordering boundary is.

5. **REVISE: E03 v2 specifies a deterministic loser for a concurrent race.**
   `tutorials/08-dataflows/03-events/v2/plan.md`, final paragraph, says the
   second append conflicts and the first is retained. The current tutorial
   at lines 62-67 races two independent connections and accepts either
   `OrderPaid` or `OrderCancelled` as winner. Its replay asserts versions
   `[1,2]` and one conflict. State exactly one success and one conflict,
   preserving whichever writer wins; do not promise submission-order victory.

These are contract corrections, not requests to add field labels or expand
the implementations. No issue is raised merely for a terminal version having
no successor. Topic-level boundaries can supply context for a short version
plan when they remain consistent with its tutorial and tests.

## Scope and method

Wave-17's 63 lexical candidates minus the 40 plans already reviewed in
waves 18/19 leave 23 candidates: F02 v0-v4, R04 v0-v3, D04 v0-v4,
P03 v0-v4, and E03 v1-v4. E03 v0 was read for continuity. F01 v0-v3
was checked as explicitly requested, though it was not in the lexical
candidate list. Total: 28 version assessments, including five context checks.

Read current plans, corresponding tutorial checkpoint/observation sections,
and replay/unit-test contracts. For identified mismatches, inspected the
underlying complete checkpoint source. This is a semantic documentation
review; no database or other runtime experiment was started and no previous
runtime verdict is replaced by this evidence.

## Per-version verdicts

| Version | Verdict | Concrete evidence and boundary |
| --- | --- | --- |
| F02 v0 | PASS | 40 completions plus measured queue growth, allocation and wait; unbounded admission motivates v1. Tutorial asserts all four observations. |
| F02 v1 | PASS | 50 arrivals partition into accepted/rejected, rejection positive, in-flight at most 3; concurrency bound explicitly does not shape rate. |
| F02 v2 | PASS | Injected clock separates initial burst from half-second refill; token-bucket unit test exhausts two tokens then admits after 0.5 s; process-local clock boundary stated. |
| F02 v3 | PASS | Round-robin 50/50 versus least-loaded tail latency; test requires both workers used and fast count greater; local-load/no-failure-detector limit stated. |
| F02 v4 | PASS | 40 completed jobs, at most 4 admitted, per-producer wait and latency output; tutorial assertions support local backpressure, not a distributed throughput claim. |
| R04 v0 | PASS | Tutorial checks PostgreSQL 16, recovery mode, streamed row and sender state; physical whole-cluster boundary motivates selection in v1. |
| R04 v1 | PASS | Publication rows converge while unpublished relation stays absent; tutorial/replay assert absence; DDL/sequence/identity limits motivate v2. |
| R04 v2 | PASS | Source/standby note column, absent subscriber note column before manual alignment, sequence 2 versus 1, identity rejection; limitations probe is the version's one teaching experiment. |
| R04 v3 | PASS | Tutorial asserts retained WAL rises then falls; replay also requires 20,001 subscriber rows; explicit workload/disk boundary, legitimate terminal version. |
| D04 v0 | PASS | Reserve and charge survive forced shipment failure; unit test asserts partial sets; persisted progress is a concrete next concern. |
| D04 v1 | REVISE | Finding 1: printed status is done, checkpoint does not restart, and effect/marker atomicity remains unresolved. |
| D04 v2 | REVISE | Finding 2: expected reverse order contradicts tutorial and unit-test effects. |
| D04 v3 | PASS | Two TimeoutError attempts produce `manual` and status tuple with attempts=2; remote idempotency explicitly excluded. |
| D04 v4 | PASS | Order/operation key returns true once, duplicate false, independent order true; thread test sums two successes; demo's local SQLite in-memory boundary is stated. |
| P03 v0 | REVISE | Finding 3: initial prerequisite is impossible; eight preserved reads and paused-write observation are otherwise specific. |
| P03 v1 | PASS | Watermark 4, new key readable from old route but absent at target; unresolved delta replay is explicit. |
| P03 v2 | REVISE | Finding 4: dedup/tombstone observations match; unordered-delivery pressure exceeds the stated ordered-log mechanism. |
| P03 v3 | PASS | Route version 2, six preserved values and stale-route rejection; local deterministic barrier boundary and restart gap are present. |
| P03 v4 | PASS | JSON state handed to child, stale fence rejected, new-owner key 9 becomes 99; explicit no-durable-storage/no-network limit prevents treating this as power-loss recovery. |
| E03 v0 (context) | PASS | Current `paid` state cannot recover history; `history_available=false` asserted by replay; next fact-stream baseline clear. |
| E03 v1 | PASS | SQLite stream/version identity and ordered replay reach shipped; invalid transition rejected; expected-version race is the next gap. Topic plan supplies single SQLite/no cross-service transaction limits. |
| E03 v2 | REVISE | Finding 5: mechanism and one-conflict invariant fit, but submitted second writer need not be the loser. |
| E03 v3 | PASS | Three applied events, duplicate suppressed, contiguous-position rejection and lagged rebuild to shipped; source remains authoritative; topic boundary excludes distributed projection coordination. |
| E03 v4 | PASS | Upcast missing currency to USD, rebuild sends zero effects, explicit new dispatch sends one; external idempotency remains excluded, no successor needed. |
| F01 v0 (context) | PASS | Three separately closed connections and SELECT 1 timing baseline; client-time/session-creation cost bounded explicitly. |
| F01 v1 (context) | PASS | Official bounded pool and connection context; sequential identity reuse at size 1 is an observation, not permanent backend identity. |
| F01 v2 (context) | PASS | Held-slot PoolTimeout followed by post-exception SELECT 1; timeout is not misidentified as database death. |
| F01 v3 (context) | PASS | Two proxy clients share PID; SET LOCAL/temp table disappear, direct pooled application_name persists, transaction returns IDLE; no universal reset/multiplexing guarantee. |

## Verdict and change boundary

REVISE for the five concrete plan inconsistencies above. Remaining 18 lexical
candidates pass semantic review; all five additional context checks pass.
No mechanical-label edits are needed for these passes. This review adds only
this evidence document, introduces no code abstraction, and creates no
temporary helpers or implementation cleanup work.
