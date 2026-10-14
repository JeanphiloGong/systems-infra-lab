# F02 v0: unbounded queue

Scenario: 40 arrivals feed a slower worker. The naive queue accepts everything, so in-flight work and memory grow while callers wait.

Pressure/checkpoint: freeze `unbounded.py`; assert `completed=40`, `peak_queue>1`, `peak_traced_bytes>0`, and `max_queue_wait_seconds>0`. These are measured counters, not estimates.

Limit/next: there is no rejection or admission bound. v1 adds a fixed in-flight limit.

Replay: `uv run python tests/traffic/admission/replay_f02.py` (the replay extracts each fence and runs an isolated interpreter).
