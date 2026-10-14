# F02 v4: backpressure reaches the producer

Scenario: 40 jobs arrive while workers are delayed. Admission must block producers instead of silently accepting unbounded work.

Pressure/change: freeze `backpressure.py` with four admitted slots and producer wait futures.

Checkpoint: every job records a wait; `completed == 40`, `max_in_flight <= 4`; print worker delays, producer seconds, max wait, p95 and max latency.

Limit/next: this is a local asyncio experiment, not a distributed queue or throughput benchmark. Later work adds durable queueing.

Replay: `uv run python tests/traffic/admission/replay_f02.py`.
