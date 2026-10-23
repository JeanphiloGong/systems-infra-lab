# F01 v3: session state and multiplexing boundary

Scenario: two logical clients reuse a backend session. Request-local settings must not become a shared contract, and a returned connection must have finished its transaction.

1. **Pressure/naive:** assume pool return clears every `SET` value or that two borrowers can interleave one protocol.
2. **Break:** `proxy.py` asserts two clients share one backend PID while `SET LOCAL` and a temporary table disappear. `session_boundary.py` observes `application_name` persisting across a pool return.
3. **Change/check:** freeze both fences. Expect `clients=2`, equal backend PIDs, `session_table_survived=False`; then `reused_session=True`, `application_name_after_return='f01-v3'`, and transaction status `IDLE`.
4. **Freeze/limit/next:** this probes PostgreSQL/PgBouncer contracts, not arbitrary protocol multiplexing or a universal reset policy.

Checkpoints: `proxy.py` and `session_boundary.py` in `tutorial.md`.

Replay:

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
export SYSTEMS_LAB_POOL_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:56432/systems_lab'
docker compose -f infra/postgres.compose.yaml -f infra/pgbouncer.compose.yaml up -d --wait
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

Requires PostgreSQL, PgBouncer on port 56432, and Docker Compose.
