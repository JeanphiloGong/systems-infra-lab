# Wave-23 D03/T04 runtime evidence

## Scope and services

Validated the D03 distributed-commit and T04 serializability modules against
real PostgreSQL. No source, tutorial, plan, progress, or index file needed a
behavioral fix.

D03 used the already-running disposable container `systems-d03-postgres` on
127.0.0.1:55434. It reported PostgreSQL accepting connections,
`max_prepared_transactions=20`, and zero leftover `d03_%` prepared
transactions before/after the run. This container was pre-existing (not
started by this wave), so it was not removed by this wave.

T04 had no usable service with the documented credentials. I started a
dedicated no-volume container `systems-wave23-t04` on 127.0.0.1:55435 using the
pinned PostgreSQL 16 image, waited for `pg_isready`, ran the suite, and removed
the container afterward. No volume was created.

## Commands and results

```bash
D03_DATABASE_URL='postgresql://d03:d03_local_only@127.0.0.1:55434/d03' \
  uv run pytest tests/coordination/commit -q
# 9 passed in 9.69s

SYSTEMS_LAB_DATABASE_URL='postgresql://t04:t04_local_only@127.0.0.1:55435/t04' \
  uv run pytest tests/transactions/serializable -q
# 6 passed in 1.68s
```

D03 coverage included v0/v1 real PostgreSQL transfer behavior, v2 commit and
abort paths, missing/partial recovery paths, v3 phase transitions, v4
partition counterexample, durable decision immutability, and prepared cleanup.
T04 coverage included printed-fence replay for v1-v3 plus live PostgreSQL
serialization abort, retry, metrics, and conflict checks.

The earlier T04 replay attempt against the ambient environment failed because
`SYSTEMS_LAB_DATABASE_URL` was unset and the available port-5433 container did
not accept the documented credentials. That was an environment problem; the
dedicated run above passed all six tests.

No new abstraction was added and no cleanup beyond removing the wave-owned
T04 container was required.
