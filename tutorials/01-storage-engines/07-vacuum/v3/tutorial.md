# S07 v3：比较普通VACUUM与VACUUM FULL，后者需更强锁并重写关系

前置v2。实验只连接本仓库PostgreSQL临时实例并创建唯一s07_ schema。逻辑COUNT与pg_stat统计分开记录；统计刷新和后台调度均有近似性，不能把一次观测推广到所有MVCC数据库。

## 完整 checkpoint

完整 `labs/storage/vacuum/full.py`：

<!-- checkpoint: labs/storage/vacuum/full.py -->

```python
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from threading import Event
from time import monotonic

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema, churn


def compare(reader: psycopg.Connection, worker: psycopg.Connection, observer: psycopg.Connection) -> tuple[int, int, int]:
    churn(worker, 20)
    worker.execute("VACUUM (TRUNCATE FALSE) items")
    ordinary = worker.execute("SELECT pg_relation_size('items')").fetchone()[0]
    entered = Event()

    def full() -> None:
        entered.set()
        worker.execute("VACUUM FULL items")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with reader.transaction():
            reader.execute("SELECT count(*) FROM items").fetchone()
            worker.execute("SET statement_timeout='10s'")
            future = pool.submit(full)
            if not entered.wait(timeout=3):
                raise TimeoutError("FULL worker did not start")
            deadline = monotonic() + 5
            while reader.info.backend_pid not in observer.execute("SELECT pg_blocking_pids(%s)", (worker.info.backend_pid,)).fetchone()[0]:
                if monotonic() >= deadline:
                    raise TimeoutError("FULL did not wait for reader")
        future.result(timeout=12)
    rewritten = worker.execute("SELECT pg_relation_size('items')").fetchone()[0]
    logical = worker.execute("SELECT count(*) FROM items").fetchone()[0]
    return ordinary, rewritten, logical


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as reader, psycopg.connect(dsn, autocommit=True) as worker, psycopg.connect(dsn, autocommit=True) as observer:
        schema = create_schema(worker)
        try:
            reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            print(compare(reader, worker, observer))
        finally:
            worker.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

初始化SQL由入口创建1000行items；运行：

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python -m labs.storage.vacuum.full
uv run python -m pytest tests/storage/vacuum -q
```

compare在普通VACUUM后记录大小，再让reader持有读事务，VACUUM FULL在worker中等待，通过pg_blocking_pids确认锁边界后释放；最终大小和COUNT实际报告。
