# R04 v1: selective logical publication

Scenario: a publisher exposes only selected tables to a subscriber; `unpublished` must remain absent while published rows converge.

Pressure/change: create logical publication/subscription and insert source data, then verify subscriber schema and rows through the common connection helper.

Checkpoint: subscriber `to_regclass('public.unpublished')` is `NULL`, and the experiment JSON reports only published data.

Limit/next: DDL, sequences, and replica identity rules are not transparent. v2 makes those limitations explicit.

Replay: `uv run pytest tests/replication/postgres -q`.

External limit: requires the R04 Compose PostgreSQL stack.
