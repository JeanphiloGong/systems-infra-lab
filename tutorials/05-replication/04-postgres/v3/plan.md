# R04 v3: paused logical consumer retains WAL

Scenario: pause a subscriber slot while the publisher generates changes, then resume and consume the backlog.

Pressure/change: record retained WAL before/after a large batch, resume the subscriber, and verify slot progress and recovered row count.

Checkpoint: `after > before`, and after recovery `recovered < after` (retained backlog decreases).

Limit: retained bytes depend on PostgreSQL WAL settings and workload; this does not provide a throughput or failover guarantee.

Replay: `uv run pytest tests/replication/postgres -q`.

External limit: requires Docker Compose, physical/logical replication configuration, and sufficient WAL disk space.
