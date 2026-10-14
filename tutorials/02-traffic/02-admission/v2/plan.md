# F02 v2: token bucket admission

Scenario: a producer may send a short burst, then must respect a steady rate. The bucket starts with capacity and refills over time.

Pressure/change: freeze `token_bucket.py`; consume the initial burst, advance the injected clock by half a second, and observe deterministic refill rather than queue growth.

Checkpoint: the script prints `{'burst': ..., 'refill_after_half_second': ...}`; assert invalid capacity/rate inputs fail and refill never exceeds capacity.

Limit/next: this is one process and one clock; it does not coordinate distributed producers. v3 makes worker choice a policy.

Replay: `uv run python tests/traffic/admission/replay_f02.py`.
