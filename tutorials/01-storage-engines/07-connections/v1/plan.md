# F01 v1: bounded session reuse

Scenario: handlers borrow sessions from `psycopg_pool.ConnectionPool`; `max_size=4`, `timeout=1.0`, and `max_waiting=32` bound physical sessions and waiting borrowers.

1. **Pressure/naive:** a hand-rolled queue must reset transactions, replace broken sessions, and close on shutdown; omitting one leaks state or capacity.
2. **Break:** hold a checkout while another request arrives; the raw approach has no defined wait limit.
3. **Change/check:** freeze `pool.py` with `make_pool` validation and `with pool.connection()`. Run `SELECT 1`, print `1`, and close in `finally`; the test checks sequential reuse with `max_size=1`.
4. **Freeze/limit/next:** identity reuse is evidence from this run, not permanence after a network failure. v2 makes exhaustion and exception cleanup observable.

Checkpoint: `tutorial.md` fence `pool.py`.

Replay:

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

Requires PostgreSQL and `psycopg_pool`.
