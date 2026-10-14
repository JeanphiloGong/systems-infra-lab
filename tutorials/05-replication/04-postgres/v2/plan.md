# R04 v2: logical replication boundaries

Scenario: schema changes and sequence values diverge between primary, physical standby, and logical subscriber.

Pressure/change: add a note column, insert rows, and inspect replica identity/sequence behavior across all three destinations.

Checkpoint: primary and standby columns equal `[('note',)]`, subscriber remains empty for the unsupported DDL path, and `primary_sequence == 2` while `subscriber_sequence == 1`.

Limit/next: this is a fixed PostgreSQL setup, not a schema migration controller. v3 pauses the logical consumer and measures retained WAL.

Replay: `uv run pytest tests/replication/postgres -q`.
