# F02 v3: worker selection policy

Scenario: 100 jobs are dispatched to equal-capacity `fast` and `slow` workers. Round-robin is fair by count, while least-loaded should reduce tail latency.

Pressure/change: freeze `balancer.py` with both policies and deterministic worker latency.

Checkpoint: round-robin returns `{'fast': 50, 'slow': 50}`; least-loaded has both workers used and `max(least.latencies) < max(rr.latencies)`.

Limit/next: the policy sees local load only and has no worker failure detector. v4 measures producer backpressure against slow service.

Replay: `uv run python tests/traffic/admission/replay_f02.py`.
