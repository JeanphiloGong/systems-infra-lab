# R04 v0: physical streaming replication

Scenario: a primary PostgreSQL 16 instance commits an update while a standby replays its WAL stream. The client must distinguish primary writability from standby recovery mode.

Pressure/change: freeze the Compose stack, init SQL, replication scripts, common helpers, and `v0.py`; verify primary version 16, standby `pg_is_in_recovery()`, streamed row `(1, 'streamed')`, and a `streaming` sender.

Limit/next: physical replication copies the whole cluster and has no selective subscriber. v1 adds logical publication/subscription.

Replay: `uv run pytest tests/replication/postgres -q` and `uv run python labs/replication/postgres/v0.py`.

External limit: requires Docker Compose and PostgreSQL containers.
