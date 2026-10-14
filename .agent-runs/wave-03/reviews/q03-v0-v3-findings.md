# Q03 v0-v3 independent review

Verdict: not accepted yet against the full roadmap scope.

The complete fences replay and focused tests pass:

```text
uv run pytest tests/query/planner -q
3 passed
uv run python tests/query/planner/replay_q03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

v0-v2 demonstrate seq/index cost choice, stale-statistics plan change, and
correlation breaking an independence estimate. v3 reports join CPU units and
sort spill bytes, but the roadmap explicitly requires comparing join strategy
and sort spill while reporting the relationship among CPU, I/O, memory, and
execution time. The printed checkpoint has no execution-time or I/O metric and
no memory measurement beyond the arbitrary `memory_rows` input. Add explicit
resource dimensions and a comparison of at least two join/sort choices, while
keeping estimates separate from observations.

No reviewer source or tutorial edits were made.
