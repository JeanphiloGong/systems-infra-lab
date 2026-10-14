# F01 v0: one connection per operation

Scenario: a request handler runs `SELECT 1` against PostgreSQL. Opening and closing a TCP session for every request is the measurable baseline.

1. **Pressure/naive:** call `connect_many(3)` and record `connections=3`; each call owns one connection and closes it in a `finally` path.
2. **Break:** repeat the short query under load; startup/authentication is paid three times and there is no concurrency bound. The failure is cost and unbounded session creation, not incorrect SQL.
3. **Change/check:** freeze `direct.py` with `connect_query`, `connect_many`, and `measure_once`. Expect a result dictionary containing `value=1`, non-negative timing fields, and `connections=3`.
4. **Freeze/limit/next:** replay the complete fence in a temporary directory. This measures client wall time against PostgreSQL; it does not measure server latency or pool reuse. v1 adds an official bounded pool.

Checkpoint: `tutorial.md` fence `direct.py`; acceptance is `SELECT 1` success and clean close on every operation.

Replay:

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

Requires the repository PostgreSQL service; extract the fence to run `direct.py` directly.
