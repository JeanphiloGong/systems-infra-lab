# F01 and S07 final independent review

## F01

Verdict: pass.

The four tutorials use the official `psycopg_pool.ConnectionPool`, the
standard `SYSTEMS_LAB_DATABASE_URL`, and complete checkpoint fences. The
replay extracts each checkpoint into a fresh temporary directory and executes
all non-pytest command lines from each printed check block. The v3 tutorial
now explicitly records the installed behavior: transaction ownership resets,
but `application_name` persists across pool return, so request-specific state
must be set or cleared inside every checkout.

```text
uv run pytest tests/traffic/connections -q
5 passed in 0.37s
uv run python tests/traffic/connections/replay_f01.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

Replay output included successful direct query, pool reuse, bounded timeout,
exception recovery, session-state observation, and idle transaction status.

## S07

Verdict: pass against the original roadmap scope.

The series distinguishes logical row count from dead-tuple statistics (v0),
ordinary VACUUM reuse without assuming immediate file shrink (v1), a
repeatable-read snapshot surviving updates and VACUUM (v2), VACUUM FULL size
and lock behavior (v3), and bounded autovacuum observation with an explicit
`observed=False` result (v4). Each experiment creates an isolated schema and
uses `relid='items'::regclass` after setting that connection's search path.

The updated replay extracts the v0 base and each v1-v4 module into separate
fresh temporary packages, runs every checkpoint against the real PostgreSQL
service, and asserts semantic outputs rather than merely checking fences.

```text
uv run pytest tests/storage/vacuum -q
6 passed in 2.89s
uv run pytest tests/storage/vacuum/test_s07_replay.py -q
2 passed in 2.19s
```

The independently observed CLI values were: v0 logical rows 1000; v1
reuse tuple `(40960, 40960, 40960, 1000)`; v2 snapshot `(0, 1000, 1000)`;
v3 ordinary/full sizes `(704512, 40960, 1000)`; and v4 bounded timeout with
`observed=False`, zero autovacuum runs, and an elapsed time near zero. Exact
tutorial hashes are recorded by the frozen files; no reviewer source edits
were made.
