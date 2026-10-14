# S03 build evidence

Scope: S03 v0-v5, tutorials/01-storage-engines/03-wal-and-recovery, labs/storage/wal, tests/storage/wal. Runtime `uv run python --version`: Python 3.14.0, guides require 3.12+. No Git commits or shared project edits.

## Increment checks

- v0 RED: `uv run pytest tests/storage/wal/test_s03_baseline.py -q` failed2 because baseline module missing; GREEN same command2 passed after implementation. Real process exit73 after Alice debit yields90/100; normal yields90/110.
- v1 RED: `uv run pytest tests/storage/wal/test_s03_framing.py -q` import failed; GREEN `uv run pytest tests/storage/wal/ -q`5 passed. Every byte prefix of second frame retains first; complete header/payload corruption raises; oversized payload rejected.
- v2 RED: `uv run pytest tests/storage/wal/test_s03_prepared.py -q` import failed; GREEN aggregate7 passed. Log intent precedes optional data write; candidate replay remains explicitly pending. Follow-up validation rejects nonstring account and negative balance; later aggregate and tutorial replay cover final edit.
- v3 RED: `uv run pytest tests/storage/wal/test_s03_store.py -q` import failed; GREEN aggregate11 passed. Committed groups only, abandoned records ignored, partial tail repair permits next commit, duplicate ID and malformed input rejected, corrupted data copy irrelevant.
- v4 RED: `uv run pytest tests/storage/wal/test_s03_durability.py -q`3 failed because event argument absent; GREEN aggregate14 passed. Exact write/flush/fsync/data/before_ack order; fsync failure never acknowledges; tail repair sync precedes append.
- v5 RED: `uv run pytest tests/storage/wal/test_s03_crash.py -q`10 failed because worker module missing; GREEN aggregate24 passed. Added9 cases with prior committed t0; crash-only command19 passed. Final aggregate `uv run pytest tests/storage/wal/ -q`:33 passed in5.18s.

## Full tutorial replay

`uv run python tests/storage/wal/replay_s03.py`: exit0. Extracts each version's marked complete source into independent TemporaryDirectory, supplies only that directory via PYTHONPATH, executes printed checks. v0=1 file, v1=1, v2=2, v3=2, v4=2, v5=3. All six printed success checks passed.

v5 independently restarts recovery twice per boundary. New store10 cases: wal_created, directory_synced, operation1, operation2, commit_written, wal_flushed, wal_synced, data_written, before_ack, after_ack. Prior committed store9 cases omit wal_created. Every result old-or-complete-new, never mixed; after ACK always committed. Fresh process models OS surviving, not power loss. Python buffered writes before flush happened to remain absent in this execution; assertions deliberately allow either absent or complete committed outcome before flush.

## Scope and correctness boundaries

Single writer; parent directory preexists and is assumed durably created. Store fsyncs newly created WAL then directory; WAL full-history authority, data.json disposable. CRC32 is accidental-corruption detection, not cryptographic protection. Incomplete tail classification assumes sequential append/truncation model; complete invalid frame errors are never silently skipped. No ARIES, checkpoint, concurrent writers, real power-loss testing, or exactly-once request guarantee claimed. Transaction ID reuse rejected, including abandoned IDs. Unknown outcomes may recover committed.

## Review and cleanup

Independent v0 PASS: reviews/s03-v0-p01-v0-v1.md. Independent v1/v2 PASS: reviews/s03-v1-v2-t02-v0.md. Reviewer required adding missing real crash at tail_repaired in v5. Added prior acknowledged t0 + incomplete tail fixture, child exit at repair completion, no ACK, two new recovery processes preserve t0, next new writer can commit and recover. Added same reader-visible check and updated plan. `uv run pytest tests/storage/wal/test_s03_crash.py -q`:20 passed in5.31s; complete six-guide replay re-run passed, v5 now reports20 cases. v3-v5 pending final independent verdict. Final suite consists of14 other tests plus20 crash tests; most recent full aggregate run was33 before the one added case, so no new aggregate count is claimed here.

Permanent teaching abstractions: framing functions, Store state/replay boundary, optional event probe for observable durability and real crash injection. Baseline/prepared retained as intentionally unsafe comparison experiments; no adapters, duplicate version implementations, or migration shims. Temporary replay directories automatically removed.
