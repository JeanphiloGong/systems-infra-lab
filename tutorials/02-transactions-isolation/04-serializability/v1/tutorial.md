# T04 v1：SERIALIZABLE 会拒绝不可串行历史

T02 的 RR 允许两个医生都下班；`SERIALIZABLE` 要求已提交历史等价某个串行执行。两个事务由 `Barrier` 同时读取，然后更新不同医生；数据库中止一方，异常离开事务块后此前更新全部回滚。

完整 checkpoint 是 `labs/transactions/serializable/serializable.py`，并由 `schema.sql` 初始化两行医生。运行：

```bash
uv run python -m labs.transactions.serializable.serializable
uv run python -m pytest tests/transactions/serializable/test_t04_serializable.py -q
```

测试使用真实 PostgreSQL，预期失败计数为1。可串行化约束事务历史，不自动定义业务规则。

## Complete checkpoint

This checkpoint's teaching boundary is only the coordinated SERIALIZABLE run: `concurrent_once` and its `leave` helper. The later `retry_once` function is shown in the evolving source only for repository continuity; do not use `--retry` until v2. The v1 acceptance is the one-abort result.

The following is the complete `labs/transactions/serializable/serializable.py` source for this checkpoint:

```python
from __future__ import annotations

import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg import sql


def leave(conn: psycopg.Connection, doctor: int, barrier: Barrier | None = None) -> bool:
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            count = conn.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
            if barrier is not None:
                barrier.wait(timeout=5)
            if count > 1:
                conn.execute("UPDATE doctors SET on_call=false WHERE id=%s", (doctor,))
        return True
    except psycopg.errors.SerializationFailure:
        return False


def concurrent_once(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int]:
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(leave, first, 1, barrier), pool.submit(leave, second, 2, barrier)]
        outcomes = [future.result(timeout=12) for future in results]
    return outcomes.count(False), first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t04_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            print(concurrent_once(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

Schema:
```sql
CREATE TABLE doctors (id integer PRIMARY KEY, on_call boolean NOT NULL);
INSERT INTO doctors VALUES (1, true), (2, true);
```

```bash
uv sync --locked
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python -m labs.transactions.serializable.serializable
uv run python -m pytest tests/transactions/serializable -q
```
