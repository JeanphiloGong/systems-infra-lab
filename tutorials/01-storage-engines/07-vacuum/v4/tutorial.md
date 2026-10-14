# S07 v4：autovacuum触发依赖阈值与后台调度，观测必须设置超时并报告未观察到

前置v3。实验只连接本仓库PostgreSQL临时实例并创建唯一s07_ schema。逻辑COUNT与pg_stat统计分开记录；统计刷新和后台调度均有近似性，不能把一次观测推广到所有MVCC数据库。

## 完整 checkpoint

完整 `labs/storage/vacuum/automatic.py`：

<!-- checkpoint: labs/storage/vacuum/automatic.py -->

```python
from __future__ import annotations

import argparse
import os
from threading import Event
from time import monotonic

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema


def observe(conn: psycopg.Connection, timeout: float) -> dict[str, int | float | bool]:
    if timeout < 0:
        raise ValueError("timeout must be nonnegative")
    conn.execute("ALTER TABLE items SET (autovacuum_enabled=true, autovacuum_vacuum_threshold=1, autovacuum_vacuum_scale_factor=0)")
    before = conn.execute("SELECT autovacuum_count FROM pg_stat_user_tables WHERE relid='items'::regclass").fetchone()[0]
    conn.execute("DELETE FROM items WHERE id<=800")
    conn.execute("SELECT pg_stat_force_next_flush()")
    start = monotonic()
    timer = Event()
    while True:
        conn.execute("SELECT pg_stat_clear_snapshot()")
        count, dead = conn.execute("SELECT autovacuum_count,n_dead_tup FROM pg_stat_user_tables WHERE relid='items'::regclass").fetchone()
        elapsed = monotonic() - start
        if count > before or elapsed >= timeout:
            return {"observed": count > before, "autovacuum_runs": count-before, "dead_estimate": dead, "elapsed_seconds": elapsed}
        timer.wait(min(0.2, timeout-elapsed))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=75)
    args = parser.parse_args()
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = create_schema(conn)
        try:
            print(observe(conn, args.timeout))
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

初始化SQL由入口创建1000行items；运行：

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python -m labs.storage.vacuum.automatic
uv run python -m pytest tests/storage/vacuum -q
```

autovacuum观测使用阈值、pg_stat_force_next_flush和有界timeout；observed=False是合法结果，不能用sleep或把等待超时写成已触发。
