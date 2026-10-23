# F01 v0: one PostgreSQL connection per operation

The first baseline is intentionally expensive: every operation opens a TCP/PostgreSQL session, runs one query, and closes it. That gives us a concrete connection lifecycle to improve. The DSN is read at the process boundary from `SYSTEMS_LAB_DATABASE_URL`; no default credential is hidden in the example.

## Pressure

Repeated short requests pay connection startup and authentication work even when the SQL is trivial. Measure the baseline before introducing a pool.

## Naive baseline

将下面的完整代码保存为 `direct.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: direct.py -->

```python
from __future__ import annotations

import os
import time
from typing import Any

import psycopg


def connect_query(sql: str = "SELECT 1") -> tuple[Any, float]:
    """Open one session, execute one statement, and close the session."""
    started = time.perf_counter()
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()[0]
    return result, time.perf_counter() - started


def connect_many(count: int) -> tuple[int, float]:
    if count < 1:
        raise ValueError("count must be positive")
    started = time.perf_counter()
    for _ in range(count):
        connect_query()
    return count, time.perf_counter() - started


def measure_once(sql: str = "SELECT 1") -> dict[str, float | Any]:
    started = time.perf_counter()
    connection = psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"])
    connected = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()[0]
        queried = time.perf_counter()
    finally:
        connection.close()
    return {"value": result, "connect_seconds": connected - started, "query_seconds": queried - connected, "total_seconds": queried - started}


if __name__ == "__main__":
    metrics = measure_once()
    count, total = connect_many(3)
    print({"metrics": metrics, "connections": count, "total_elapsed_seconds": total})
```

## Break

This is correct for one request, but a high request rate creates and tears down a session for every query. The baseline also provides no bound on concurrent sessions.

## Check and freeze

Start the repository PostgreSQL service, set its DSN, and run:

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python direct.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

</details>

The integration test checks that `SELECT 1` succeeds. This measures client-observed elapsed time, not server or disk latency. The next version keeps sessions alive in an official bounded pool.
