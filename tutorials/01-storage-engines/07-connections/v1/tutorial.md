# F01 v1: reuse sessions with an official bounded pool

Version 0 created one session per operation. `psycopg_pool.ConnectionPool` keeps a bounded number of physical PostgreSQL connections and hands an idle one to each borrower. The pool is a concurrency control boundary: `max_size` limits sessions, and `timeout` bounds how long a borrower waits.

## Pressure and break

Writing a queue around raw `psycopg.Connection` objects leaves transaction reset, broken connections, and shutdown behavior to application code. Use the maintained pool implementation instead.

## One change

<!-- checkpoint: pool.py -->

```python
from __future__ import annotations

import os

from psycopg_pool import ConnectionPool


def make_pool(min_size: int = 0, max_size: int = 4, timeout: float = 1.0, max_waiting: int = 32) -> ConnectionPool:
    if min_size < 0 or max_size < 1 or min_size > max_size or timeout <= 0 or max_waiting < 1:
        raise ValueError("invalid pool bounds")
    return ConnectionPool(
        os.environ["SYSTEMS_LAB_DATABASE_URL"],
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        max_waiting=max_waiting,
        open=True,
    )


if __name__ == "__main__":
    pool = make_pool(min_size=1, max_size=2)
    try:
        with pool.connection() as connection:
            print(connection.execute("SELECT 1").fetchone()[0])
    finally:
        pool.close()
```

`with pool.connection()` borrows a session and returns it when the block exits. It does not make two SQL statements on one connection execute concurrently. This is pooling, not protocol multiplexing.

## Check and freeze

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python pool.py
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

The reuse test checks object identity across two sequential borrows with `max_size=1`. That is evidence of reuse in this run, not a promise that a connection is never replaced after a server or network failure.
