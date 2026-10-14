# Q01 v0-v3 final rereview

Verdict: pass.

The v3 checkpoint now inserts order 11 with a new purchase price while
retaining order 10 at its original price, so current product-name updates do
not rewrite historical purchase facts. v0-v2 continue to demonstrate the
duplicate-data anomaly, normalized foreign-key join, and stale maintained read
model. Read and write cost counters remain explicit.

```text
uv run pytest tests/query/modeling -q
4 passed in 0.02s
uv run python tests/query/modeling/replay_q01.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

No reviewer source or tutorial edits were made.
