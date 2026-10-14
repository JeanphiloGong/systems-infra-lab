# Q02 build evidence

Implemented `labs/query/indexes/model.py` with secondary/composite index candidate selection, index maintenance writes, and visibility-aware heap fetch counts. Added v0-v3 tutorials, tests, and isolated replay.

Verification:

```text
uv run pytest tests/query/indexes -q
2 passed

uv run python tests/query/indexes/replay_q02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

The measurements are logical candidate/heap reads and index maintenance counts, not hardware latency claims.

Review fixes: v2 now executes composite range filters and ordered results for both `(user, day)` and `(day, user)` layouts. v3 models a visibility map cleared by an update, heap fallback, and a vacuum-like maintenance step restoring index-only reads.
