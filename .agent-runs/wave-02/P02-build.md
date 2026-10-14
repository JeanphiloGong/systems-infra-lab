# P02 build evidence

Added skew.py with deterministic SHA256 routing, per-partition request distribution, explicit salted subkey distribution and aggregation. Earlier assumption that four hashed subkeys evenly map to four partitions was false; salt routing now explicitly assigns subkeys round-robin. Added queues.py discrete model with p99, capacity bound and shared dispatcher bottleneck; v3 tutorial runs it and states units are not production latency. Isolated replay executes v0-v3 source and queues in a clean package. Final `uv run python -m pytest tests/partitioning/skew -q`: **10 passed in0.58s**. No network mocks or production latency claims; independent review pending.

Review fix: each v0-v3 tutorial now includes a complete current skew.py fence; v3 additionally includes complete queues.py. Replay extracts those fences (never current worktree source), executes every version in a clean package, and asserts v3 queue output contains p99 and capacity_bound. Strict replay: **1 passed in0.51s**; focused suite remains green.

v3 semantic fix: queues.py now asserts in executable code that unsalted hot-key p99 is unchanged from 4 to 8 partitions, salting improves p99 and capacity_bound, and shared dispatcher service caps capacity at1 with higher p99. Full focused suite after refreshed fence: **10 passed in0.63s**.
