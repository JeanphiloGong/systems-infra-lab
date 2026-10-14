# D04 v1: resume persisted Saga progress

Scenario: a file-backed Saga is closed and reopened after a forward step. The reopened coordinator must read the durable done marker without repeating that completed step.

Pressure/change: persist status and completed step calls, then close/reopen `order-1` using the same process test; the tutorial fence itself uses `:memory:` and demonstrates the normal completed path.

Checkpoint: the tutorial prints `['reserve', 'charge']` and both steps `done`; the focused test reopens a file-backed database and observes `calls == ['reserve']` after the duplicate invocation.

Limit/next: `effect()` runs before the durable `done` update, so a crash in that window can repeat an external effect; this is not arbitrary crash-safe exactly-once execution. Compensation is not modeled yet; v2 adds caller-supplied reverse compensation.

Replay: `uv run pytest tests/coordination/saga/test_replay_d04.py -q`.
