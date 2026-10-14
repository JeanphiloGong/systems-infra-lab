# F01 v2: exhaustion and exception-safe return

Scenario: `max_size=1` means one forgotten checkout can block every other request.

1. **Pressure/naive:** hold `pool.connection()` and attempt a second checkout; without a return path the second borrower waits forever.
2. **Break:** the bounded pool raises `PoolTimeout` after `0.2` seconds; a handler exception must still return the held session.
3. **Change/check:** freeze `pool_cleanup.py` with nested contexts. Expect `bounded exhaustion observed`, then `{'recovered': 1}` after a simulated `RuntimeError`; close the pool in shutdown.
4. **Freeze/limit/next:** timeout proves a held slot, not a dead database or throughput guarantee. v3 examines session state and transaction-pool boundaries.

Checkpoint: `tutorial.md` fence `pool_cleanup.py`; acceptance includes timeout and post-exception recovery.

Replay:

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

Requires the repository PostgreSQL service.
