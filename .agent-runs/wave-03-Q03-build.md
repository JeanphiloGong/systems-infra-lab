# Q03 build evidence

Implemented `labs/query/planner/model.py` with selectivity-based plan choice and correlation-aware join estimates. Added v0-v3 tutorials, tests, and isolated replay.

Verification:

```text
uv run pytest tests/query/planner -q
3 passed

uv run python tests/query/planner/replay_q03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

The examples separate estimated costs from observed rows and report logical CPU/spill units rather than claiming database timing.

v3 now compares nested-loop and hash joins plus in-memory and chunked external sorts, recording wall-clock samples, rows read, comparison/probe counts, chunk count, and spill bytes. Timing is local evidence only.
