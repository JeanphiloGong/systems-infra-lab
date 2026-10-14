# A03 v4: rebuild, catch up, and planned switchover

Scenario: the old primary returns after isolation. It must be rebuilt or caught up as a replica before a planned role switch; a stale data directory cannot be trusted directly.

Pressure/change: run the full Patroni probe sequence, restore the old node, verify convergence, then perform the planned switchover.

Checkpoint: output preserves the v2/v3 isolation assertions and reports a caught-up old node before role change; client reads remain consistent through switchover.

Limit: Docker-local HA and fixed topology; no geo-failover or arbitrary network partition proof.

Replay: `uv run python -m labs.recovery.ha.patroni_probe` and `uv run pytest tests/recovery/ha -q`.

External limit: requires Docker, Patroni, PostgreSQL, and cleanup of the lab stack.
