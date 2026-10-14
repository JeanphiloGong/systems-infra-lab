# A02 v1-v3 repair review: PASS

Scope reviewed: `labs/recovery/checkpoint/store.py`, the checkpoint
experiments/tests, and the v1-v3 tutorial fences. v0's CRC-framed transaction
format, contiguous replay, nonnegative balances, and total-preservation rules
remain the source of truth.

Executed evidence:

- `uv run python tests/recovery/checkpoint/replay_a02.py` passed. It extracted
  `framing.py`, `baseline.py`, and `store.py` from each tutorial, compared each
  fence with the repository source, ran in an isolated temporary package, and
  exercised version-specific behavior:
  - v1 recovered position 15 after snapshot position 10 and five tail commits.
  - v2 published position 5, reclaimed all five covered WAL files, and
    recovered position 5.
  - v3 corrupted the newest generation and recovered position 25 through the
    older snapshot plus its 15-transaction tail.
- `uv run pytest -q tests/recovery/checkpoint` passed: **16 passed**.
- `uv run python -m labs.recovery.checkpoint.experiments 1` observed 816 bytes
  read for the five post-snapshot transactions, less than the full WAL.
- Experiment 2 observed fresh-process recovery after snapshot and publication
  exits 71, 72, 73, and first-log-delete exit 74.
- Experiment 3 observed fallback after corrupting the latest snapshot, explicit
  failure for a missing required segment and unusable bases, generation
  rotation exits 71 through 75, and continued recovery at position 31.

The previous reopen findings are addressed: snapshots are published and used
for recovery, publication validates every retained base before reclaiming,
required tails are retained, corrupt or missing bases never reset to initial
state, and obsolete generations are removed only after the manifest and log
reclamation steps.

Decision: **PASS** for A02 v1-v3. No new abstraction was added; the repair
keeps the existing Store boundary and removes stale tutorial/test assumptions.
