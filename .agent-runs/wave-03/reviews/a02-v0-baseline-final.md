# A02 v0 baseline independent review

Verdict: PASS for the original A02 v0 scope in `docs/roadmap.md:614`. This is only v0; the planned snapshot, atomic publication/reclamation and fallback checkpoints are not claimed.

## Actual verification

Ran `uv run pytest tests/recovery/checkpoint -q`: **5 passed in 0.30s**.

The tests independently verify empty/full history recovery (10 real WAL segment files and measured byte count), ignore an unfinished `.tmp`, reject missing middle segments, reject truncation and CRC damage, reject invalid transactions before publication, reject duplicate segment numbers, and replay the exact tutorial fences in a temporary directory with `PYTHONPATH` isolated. The tutorial fence test includes the S03 framing dependency and executes a fresh probe against extracted code; it does not rely on the current worktree baseline implementation.

## Semantics checked

`commit` writes two account updates plus a commit frame to an fsynced temporary file, atomically publishes the numbered `.wal` segment and fsyncs the directory. `recover` scans the complete ordered prefix, decodes and validates every segment, replays all records from the initial state, and reports actual transaction count and bytes read. Temporary files are ignored; any published gap, incomplete frame, wrong transaction position, invalid transfer, or checksum failure aborts recovery rather than returning partial balances.

The full-log cost pressure is real: the 10-segment test counts filesystem bytes and transactions, and each segment is decoded. The module deliberately has no snapshot or log reclamation yet, matching v0's boundary and the plan's next-step handoff.

## Boundaries

This is a local single-writer teaching format using S03's framing/CRC; directory fsync and process-level tests are not a power-loss proof. The `replay` helper's unused `used` return set is harmless to v0 behavior but should not be mistaken for checkpoint metadata. Snapshot versions v1-v3 remain unimplemented and require separate review.

Review artifact only; no implementation abstraction or source cleanup added.
