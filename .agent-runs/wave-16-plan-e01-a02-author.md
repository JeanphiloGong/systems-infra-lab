# E01/A02 version-plan revision evidence

Rewrote all nine version plans with concrete scenarios, previous-version
gaps, deterministic pressure/failure, one mechanism change, exact assertions
or outputs, freeze artifact, limits, next pressure, and version-specific
replay commands.

- E01 v0-v4 cover source/projection divergence, logical WAL events,
  snapshot-plus-tail, transactional projection checkpoints, and retained WAL
  during a paused consumer.
- A02 v0-v3 cover full WAL replay, snapshot tail recovery, publication-before-
  reclaim crash boundaries, and retained-generation fallback.

Verification:

```text
$ uv run pytest tests/recovery/checkpoint -q
16 passed
$ uv run pytest tests/dataflows/cdc -q
1 passed, 7 failed (PostgreSQL unavailable at 127.0.0.1:55450)
```

The E01 failures are environment limitations, not claimed passes: tests
require `infra/e01.compose.yaml` and `E01_DATABASE_URL` for a real PostgreSQL
logical replication slot. A02 is self-contained and passed. No code, tutorial
body, docs/progress, or index files were changed.
