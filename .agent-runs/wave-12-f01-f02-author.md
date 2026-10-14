# F01/F02 source-of-truth repair evidence

Closed the independent review's implementation-boundary findings.

F01 now has repository source files for every tutorial checkpoint:
`direct.py`, `pool.py`, `pool_cleanup.py`, `proxy.py`, and
`session_boundary.py` under `labs/traffic/connections/`. The missing cleanup
and session-boundary programs were added from the complete tutorial fences.
F02 now synchronizes `unbounded.py`, `bounded.py`, `token_bucket.py`, and
`balancer.py` with their executable tutorial assertions and adds the missing
`backpressure.py` source. New parity tests compare every referenced fence to
its lab file byte-for-byte after trailing whitespace normalization.

```text
$ uv run pytest tests/traffic/connections/test_fence_parity.py tests/traffic/admission/test_fence_parity.py -q
2 passed
$ uv run python tests/traffic/admission/replay_f02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
$ uv run pytest tests/traffic/admission/test_f02_admission.py -q
5 passed
$ uv run pytest tests/traffic/connections/test_f01_pool.py -q
6 skipped
$ uv run python tests/traffic/connections/replay_f01.py
SKIP: set SYSTEMS_LAB_DATABASE_URL for live PostgreSQL replay
```

F01 live behavior remains unverified in this environment because PostgreSQL
is unavailable; v3 additionally needs the PgBouncer Compose service and
`SYSTEMS_LAB_POOL_URL`. The six skipped tests are an explicit environment
limit, not a pass claim. No tutorial body, plans, docs/progress, or indexes
were changed. No new abstraction was added; the two parity tests are
permanent source-of-truth checks.
