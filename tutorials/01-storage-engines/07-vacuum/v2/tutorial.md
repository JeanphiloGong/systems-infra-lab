# S07 v2：长REPEATABLE READ快照仍读旧值，VACUUM不能回收它所需版本

前置v1。实验只连接本仓库PostgreSQL临时实例并创建唯一s07_ schema。逻辑COUNT与pg_stat统计分开记录；统计刷新和后台调度均有近似性，不能把一次观测推广到所有MVCC数据库。

## 完整 checkpoint

完整 `labs/storage/vacuum/snapshot.py`：

<!-- checkpoint: labs/storage/vacuum/snapshot.py -->

```python
from __future__ import annotations

import os

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema


def observe(reader: psycopg.Connection, writer: psycopg.Connection) -> tuple[int, int, int]:
    with reader.transaction():
        reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        before = reader.execute("SELECT sum(value) FROM items").fetchone()[0]
        writer.execute("UPDATE items SET value=1")
        writer.execute("VACUUM items")
        old_snapshot = reader.execute("SELECT sum(value) FROM items").fetchone()[0]
        current = writer.execute("SELECT sum(value) FROM items").fetchone()[0]
    writer.execute("VACUUM items")
    assert before == old_snapshot
    return old_snapshot, current, reader.execute("SELECT sum(value) FROM items").fetchone()[0]


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as reader, psycopg.connect(dsn, autocommit=True) as writer:
        schema = create_schema(writer)
        try:
            reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            print(observe(reader, writer))
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

初始化SQL由入口创建1000行items；运行：

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python -m labs.storage.vacuum.snapshot
uv run python -m pytest tests/storage/vacuum -q
```

reader在第一条SELECT建立RR快照，writer更新并VACUUM；reader仍读旧总和，writer读新值。快照结束后再清理。
