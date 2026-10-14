# S07 v1：普通VACUUM后删除空间可复用而文件通常不缩小

前置v0。实验只连接本仓库PostgreSQL临时实例并创建唯一s07_ schema。逻辑COUNT与pg_stat统计分开记录；统计刷新和后台调度均有近似性，不能把一次观测推广到所有MVCC数据库。

## 完整 checkpoint

完整 `labs/storage/vacuum/reuse.py`：

<!-- checkpoint: labs/storage/vacuum/reuse.py -->

```python
from __future__ import annotations

import os

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema


def reuse(conn: psycopg.Connection) -> tuple[int, int, int, int]:
    before = conn.execute("SELECT pg_relation_size('items')").fetchone()[0]
    conn.execute("DELETE FROM items WHERE id<=800")
    conn.execute("VACUUM (TRUNCATE FALSE) items")
    cleaned = conn.execute("SELECT pg_relation_size('items')").fetchone()[0]
    conn.execute("INSERT INTO items SELECT i,0 FROM generate_series(1,800) AS i")
    after = conn.execute("SELECT pg_relation_size('items')").fetchone()[0]
    count = conn.execute("SELECT count(*) FROM items").fetchone()[0]
    return before, cleaned, after, count


def main() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = create_schema(conn)
        try:
            print(reuse(conn))
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

初始化SQL由入口创建1000行items；运行：

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python -m labs.storage.vacuum.reuse
uv run python -m pytest tests/storage/vacuum -q
```

普通VACUUM清理可复用空间，不承诺pg_relation_size下降；测试用删除后重新插入观察大小和逻辑行。
