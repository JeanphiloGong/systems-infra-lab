# Q02 v0-v3 final rereview

Verdict: pass.

The v2 checkpoint now executes composite range filtering and explicit ordering
for both `(user, day)` and `(day, user)` column orders, with distinct candidate
sets and sorted result assertions. v3 models a visibility map, invalidates a
row after update, counts the resulting heap fetch, refreshes visibility with
a VACUUM-like step, and verifies index-only eligibility returns.

Independent verification:

```text
uv run pytest tests/query/indexes -q
2 passed in 0.02s
uv run python tests/query/indexes/replay_q02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

All four complete fences are extracted and executed in fresh subprocesses.
No reviewer source or tutorial edits were made.
