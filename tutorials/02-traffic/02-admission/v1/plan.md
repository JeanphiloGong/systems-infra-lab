# F02 v1: bound in-flight work

Scenario: 50 arrivals contend for workers. A bounded semaphore admits only three concurrent jobs and rejects excess work explicitly.

Pressure/change: replace the unbounded queue with `bounded.py`; keep completed work observable while making rejection and `max_in_flight` measurable.

Checkpoint: assert `accepted + rejected == 50`, `rejected > 0`, and `max_in_flight <= 3`; print the result object.

Limit/next: this limits concurrency but does not shape arrival rate. v2 adds token refill and bursts.

Replay: `uv run python tests/traffic/admission/replay_f02.py`.
