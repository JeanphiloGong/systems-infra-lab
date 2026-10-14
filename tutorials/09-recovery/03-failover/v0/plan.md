# A03 v0: model failover targets

Scenario: a primary fails after acknowledging a set of writes. A client needs a new writable target, with explicit RTO/RPO rather than an invented promotion duration.

Pressure/change: freeze model and experiment version 0 with a logical clock, confirmed data set, and promotion outcome.

Checkpoint: replay executes only version 0 and reports the modeled recovered target/data; no real outage timing is claimed.

Limit/next: no process promotion or fencing. v1 adds a human-controlled promotion decision.

Replay: `uv run python tests/recovery/ha/replay_a03.py`.
