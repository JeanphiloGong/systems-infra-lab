# Q01 v0-v3 independent review

Verdict: not accepted yet.

The extracted checkpoints replay and focused tests pass, and v0-v2 clearly
show the intended anomaly, foreign-key join, stale read model, and maintenance
write tradeoff. One v3 semantic defect remains: the example mutates
`orders[10]` from price 12 to 13 and then calls that value a new historical
snapshot. That rewrites the existing purchase fact and violates the roadmap
invariant that business history must not be changed by current-information
updates. Insert a distinct new order (for example order 11) while retaining
order 10 at price 12, then assert both snapshots.

Independent verification:

```text
uv run pytest tests/query/modeling -q
3 passed
uv run python tests/query/modeling/replay_q01.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

No reviewer source or tutorial edits were made.
