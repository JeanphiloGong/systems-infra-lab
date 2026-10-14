# A03 v3: old primary is alive but locally unwritable

Scenario: only the old primary's network is cut. It remains running, but a local write must fail while the promoted node remains authoritative.

Pressure/change: run a fresh isolated Patroni experiment and assert old-primary write rejection plus container liveness.

Checkpoint: probe returns nonzero for the isolated old primary, Docker reports it still running, and retained acknowledged data is present.

Limit/next: no full-machine failure, bidirectional selective link matrix, or long-running transaction. v4 rebuilds the old node and catches it up before planned switchover.

Replay: `uv run python -m labs.recovery.ha.patroni_probe` and `uv run pytest tests/recovery/ha -q`.

External limit: requires the Patroni Docker lab.
