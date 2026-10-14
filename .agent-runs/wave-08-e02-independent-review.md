# E02 Repair Review: PASS

Independently started `infra/e02.compose.yaml` with up -d --wait, executed
`E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest tests/dataflows/schema_evolution -q`, and observed **6 passed in 5.20s**.
Then down -v removed the dedicated container and network successfully.

Read all revised implementation branches and the corresponding complete
fences/tests. The live suite extracts common.py and each vN.py, checks source
equality, and runs a fresh subprocess in its temporary package. Event tests
also execute the extracted consumers without a database URL.

The original-scope findings are closed:

- v0 obtains real 23502 errors separately for old INSERT after adding a
  required column to an empty table, and DDL on a populated table. The rename
  read failure remains as an explicitly separate example.
- v1 checks old/new inserts, reads and same-row updates using separate
  connections. It observes stale COALESCE after old update and verifies the
  authoritative legacy-field policy. Six event producer/consumer combinations
  and absent-field rejection are independently asserted.
- v2 repairs the divergent field before NULL-only backfill, then runs fresh
  workers with exits 17/19, checks rollback and durable progress, reads actual
  resumed/repeated counts 2/0, and preserves the designated new-client value.
  The whole extracted experiment runs twice against the same database.
- v3 blocks contraction while an old client is active or backfill is incomplete;
  it then checks final catalog state, legacy-column removal, three actual
  23502 write failures, valid final writes/reads, and removal of both migration
  tables. Its final event reader has no name fallback and rejects old, missing,
  NULL and empty payload values. Independent connections verify cleanup.

Accepted boundary: old writers are drained before cursor/final synchronization;
the client registry is a controlled readiness input, not deployment fencing.
The source describes this assumption and does not claim arbitrary concurrent
rolling-upgrade safety. This verdict supersedes wave-07 E02 scope REVISE for
the repaired checks, retaining the historical evidence separately.

Only this review artifact was added. No author files, progress or index changed;
no abstraction was added. Cleanup removed only the review's disposable stack.
