# Q02 v0-v3 independent review

Verdict: not accepted yet against the full roadmap scope.

The complete fences replay and the model tests pass:

```text
uv run pytest tests/query/indexes -q
2 passed
uv run python tests/query/indexes/replay_q02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

v0 and v1 establish a sequential scan baseline and selective secondary-index
candidates. v3 demonstrates a covering projection becoming heap-visible after
an update. Two scope gaps remain:

- v2 only counts equality candidates for `(user, day)` versus `(day, user)`.
  The roadmap explicitly requires comparing filtering, sorting, and range
  conditions; no range or ordering behavior is exercised.
- v3 increments a toy `heap_fetches` counter after changing a row and prints
  `vacuum_visibility_required`, but never models or executes visibility-map
  maintenance/VACUUM restoring an index-only path. The checkpoint should show
  the post-update heap fetch and a subsequent visibility-maintenance boundary,
  with the limitation clearly stated if maintenance is only modeled.

No reviewer source or tutorial edits were made.
