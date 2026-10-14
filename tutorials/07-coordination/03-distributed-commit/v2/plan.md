# D03 v2: recover coordinator obligations

Scenario: kill the actual worker after prepare, before or after recording commit/abort, then inspect both PostgreSQL databases.

Pressure/change: persist a global decision before sending it and keep missing decisions explicitly `in_doubt`; recovery resolves only known decisions.

Checkpoint: worker exits 23; partial prepare leaves one pending transaction and balances `[100,100]` with outcome `in_doubt`; commit recovers `[70,130]`, abort recovers `[100,100]`.

Limit/next: recovery depends on durable journal availability. v3 adds a pre-commit phase to expose another timing window.

Replay: `uv run pytest tests/coordination/commit -q` and the v2 commit/abort/missing/partial commands.
