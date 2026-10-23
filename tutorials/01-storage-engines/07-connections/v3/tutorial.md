# F01 v3: session state, transactions, and the multiplexing boundary

A pool reuses physical sessions, so session state can outlive one application request unless the pool resets it. A transaction must finish before the connection is returned. A pool also gives one borrower exclusive use of a connection; it cannot interleave two callers' protocols on that session.

## Pressure and break

If code leaves a transaction open or relies on `SET` state surviving a checkout, the next borrower can observe surprising state. Closing a checked-out connection directly is not a substitute for leaving the pool context: the pool needs the context exit to account for the checkout and perform its reset/return protocol.

## One change: make ownership explicit

When a transaction-pool proxy is available, two client connections can share one backend session. The proxy must reset transaction state between clients; it cannot preserve arbitrary session state across requests.

将下面的完整代码保存为 `proxy.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: proxy.py -->

```python
import os
import psycopg


def observe() -> dict[str, object]:
    dsn = os.environ["SYSTEMS_LAB_POOL_URL"]
    with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as first, psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as second:
        with first.transaction():
            first_pid = first.execute("SELECT pg_backend_pid()").fetchone()[0]
            first.execute("SET LOCAL application_name = 'f01-request'")
            first.execute("CREATE TEMP TABLE f01_session_only (value integer)")
        with second.transaction():
            second_pid = second.execute("SELECT pg_backend_pid()").fetchone()[0]
            assert first_pid == second_pid
            assert second.execute("SHOW application_name").fetchone()[0] != "f01-request"
            assert second.execute("SELECT to_regclass('pg_temp.f01_session_only')").fetchone()[0] is None
    return {"clients": 2, "backend_pids": [first_pid, second_pid], "session_table_survived": False}


if __name__ == "__main__":
    print(observe())
```

将下面的完整代码保存为 `session_boundary.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: session_boundary.py -->

```python
from __future__ import annotations

import os

from psycopg_pool import ConnectionPool


def main() -> None:
    pool = ConnectionPool(
        os.environ["SYSTEMS_LAB_DATABASE_URL"],
        min_size=1,
        max_size=1,
        timeout=1.0,
        open=True,
    )
    try:
        with pool.connection() as first:
            first.execute("SET application_name = 'f01-v3'")
            first.execute("SELECT 1")

        with pool.connection() as second:
            # In this installed version, transaction state is reset but this
            # application_name setting persists across the pool return.
            state = second.execute("SELECT current_setting('application_name')").fetchone()[0]
            assert state == "f01-v3"
            print({"reused_session": True, "application_name_after_return": state})

        with pool.connection() as transaction_connection:
            with transaction_connection.transaction():
                transaction_connection.execute("SELECT 1")
            # The transaction is complete before the context returns the session.
            print({"transaction_status": transaction_connection.info.transaction_status.name})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
```

The exact reset policy is a library/database contract. This run observes
`application_name` persisting, so request-specific session settings must be
set or cleared inside each checkout. The pool does reset transaction ownership
when the context exits; explicitly finish transactions before returning the
session. The PgBouncer transaction-pool checkpoint separately shows two client
connections sharing one backend PID while transaction-local state is cleared.
That is transaction pooling, not arbitrary protocol multiplexing.

## Check and freeze

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python session_boundary.py
export SYSTEMS_LAB_POOL_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:56432/systems_lab'
docker compose -f infra/postgres.compose.yaml -f infra/pgbouncer.compose.yaml up -d --wait
uv run python proxy.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

</details>

The check reports the observed persisted value and transaction status. It does
not claim that every server-side session setting is reset automatically;
application-owned state needs an explicit lifecycle policy.
