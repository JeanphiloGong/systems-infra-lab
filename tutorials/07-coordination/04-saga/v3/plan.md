# D04 v3: failed compensation needs retry and manual state

Scenario: a compensation endpoint times out twice. The coordinator must stop after its retry budget and mark the Saga for human action.

Pressure/change: freeze `v3.py` with `max_attempts=2`, retry recording, and an explicit manual/intervention status.

Checkpoint: `compensate('order-1', 1, ...)` returns failure after two attempts; the following status print is manual rather than falsely completed.

Limit/next: retries remain local and do not prove idempotency at remote services. v4 isolates concurrent orders and duplicate requests.

Replay: `uv run pytest tests/coordination/saga/test_replay_d04.py -q`.
