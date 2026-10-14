# Q03 v0-v3 final rereview

Verdict: pass.

The v3 checkpoint now compares nested-loop and hash joins, and in-memory and
chunked external sorting. It reports rows read, comparison/probe counts,
wall-clock samples, chunk count, and spill bytes, with assertions proving
equal join results and a multi-chunk spill tradeoff. v0-v2 retain the
seq/index choice, stale-statistics plan change, and correlated-field estimate
boundary.

```text
uv run pytest tests/query/planner -q
3 passed in 0.02s
uv run python tests/query/planner/replay_q03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

No reviewer source or tutorial edits were made.
