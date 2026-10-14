# R04/D04 version-plan revision evidence

Rewrote all nine version plans with concrete implementation contracts.

- R04 v0-v3 cover physical streaming, selective logical publication, DDL/
  sequence/replica-identity limits, and WAL retained by a paused consumer.
- D04 v0-v4 cover partial Saga effects, durable resume, reverse compensation,
  retry/manual intervention, and concurrent idempotent order effects.

Each plan names the scenario, previous gap, pressure/failure, one mechanism,
exact assertions or output, freeze artifact, limits, next pressure, and replay
command.

Verification:

```text
$ uv run pytest tests/coordination/saga -q
10 passed
$ uv run pytest tests/replication/postgres -q
1 passed, 4 failed
```

The R04 failures are explicit environment limits: the tests require the real
PostgreSQL Compose stack and `R04_DATABASE_URL=postgresql://r04:r04_local_only@127.0.0.1:55440/r04`; that service was not running. No code, tutorial
body, docs/progress, or index files were changed.
