# F01-F04 version-plan revision evidence

Replaced the generic task-template plans for all 16 version directories:

- F01 connections v0-v3
- F02 admission v0-v4
- F03 retry v0-v4
- F04 herd v0-v3

Each plan now names its real request scenario, the prior version's missing
behavior, deterministic pressure/break, one mechanism change, exact assertions
or printed observations from the tutorial, the complete source fence as the
freeze artifact, explicit limits, the next pressure, and a version-specific
replay command. Only these plans and this evidence file were changed; no
tutorial body, lab source, test, progress, or index file was changed.

Verification:

```text
$ uv run python tests/traffic/admission/replay_f02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok

$ uv run pytest tests/traffic/retry/test_replay_f03.py -q
12 passed

$ uv run pytest tests/traffic/herd/test_f04.py -q
4 passed

$ uv run pytest tests/traffic/connections/test_f01_pool.py -q
6 skipped
```

F01's six tests are present but skipped because the local PostgreSQL service
was not available in this run. F01 v0-v2 require
`SYSTEMS_LAB_DATABASE_URL`; v3 additionally requires the PgBouncer Compose
service and `SYSTEMS_LAB_POOL_URL`. The plan records those prerequisites
instead of treating a skipped integration test as a pass. No new abstraction
was added and no cleanup outside the requested plan files was needed.
