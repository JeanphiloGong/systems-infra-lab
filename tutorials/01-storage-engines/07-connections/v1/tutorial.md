# F01 v1: reuse sessions with an official bounded pool

Version 0 created one session per operation. `psycopg_pool.ConnectionPool` keeps a bounded number of physical PostgreSQL connections and hands an idle one to each borrower. The pool is a concurrency control boundary: `max_size` limits sessions, and `timeout` bounds how long a borrower waits.

## Pressure and break

Writing a queue around raw `psycopg.Connection` objects leaves transaction reset, broken connections, and shutdown behavior to application code. Use the maintained pool implementation instead.

## One change

将下面的完整代码保存为 `pool.py`；文件已存在时，以本版内容替换该文件。

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
    pool = make_pool(min_size=1, max_size=1)
    try:
        with pool.connection() as first:
            first_pid = first.execute("SELECT pg_backend_pid()").fetchone()[0]
        with pool.connection() as second:
            second_pid = second.execute("SELECT pg_backend_pid()").fetchone()[0]
            assert second is first
            assert second_pid == first_pid
        print({"sequential_borrows": 2, "same_connection": True, "backend_pid": second_pid})
    finally:
        pool.close()
```

`with pool.connection()` borrows a session and returns it when the block exits. It does not make two SQL statements on one connection execute concurrently. This is pooling, not protocol multiplexing.

## Check and freeze

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python pool.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

</details>

The direct program makes two sequential borrows with `max_size=1` and checks both Python object identity and PostgreSQL backend PID. Expect `sequential_borrows=2` and `same_connection=True`; the PID varies. The first context must exit before the second begins, otherwise the sole connection is still borrowed. This proves reuse in this run, not that connections survive server or network failure forever.
