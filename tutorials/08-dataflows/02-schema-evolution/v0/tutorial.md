# E02 v0：破坏性改名和必填字段

旧客户端先成功写入 Ada。直接改名使旧 SELECT 抛 UndefinedColumn；这与新增必填字段是两种独立失败。重新建空表后增加无默认值的 NOT NULL full_name，旧形状 INSERT 抛 23502。最后用已有 Ada 行的表尝试相同 DDL，DDL 自身也抛 23502。每次检查真实异常，不把 DDL 失败当作旧写失败。

仅运行专用 E02 PostgreSQL（端口 55451）。全部成功路径清理实验表；测试还从独立临时目录提取代码，确认没有依赖工作区实现。

<!-- checkpoint: labs/dataflows/schema_evolution/common.py -->

```python
from __future__ import annotations

import os

import psycopg


DSN = os.getenv("E02_DATABASE_URL", "postgresql://e02:e02_local_only@127.0.0.1:55451/e02")


def connect() -> psycopg.Connection:
    return psycopg.connect(DSN, autocommit=True, connect_timeout=3)


def reset(conn: psycopg.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS schema_backfill_checkpoint, migration_clients")
    conn.execute("DROP TABLE IF EXISTS profiles")
```

<!-- checkpoint: labs/dataflows/schema_evolution/v0.py -->

```python
from __future__ import annotations

import json
import psycopg

from common import connect, reset


def experiment() -> dict[str, object]:
    with connect() as conn:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL)")
        conn.execute("INSERT INTO profiles VALUES (1, 'Ada')")
        old_client = conn.execute("SELECT name FROM profiles WHERE id=1").fetchone()[0]
        conn.execute("ALTER TABLE profiles RENAME COLUMN name TO full_name")
        try:
            conn.execute("SELECT name FROM profiles WHERE id=1")
        except psycopg.errors.UndefinedColumn:
            broken = True
        else:
            broken = False
        assert old_client == "Ada" and broken
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL)")
        conn.execute("ALTER TABLE profiles ADD COLUMN full_name text NOT NULL")
        try:
            conn.execute("INSERT INTO profiles(id,name) VALUES (1,'Ada')")
        except psycopg.errors.NotNullViolation as error:
            old_write_error = error.sqlstate
        else:
            raise AssertionError("old writer unexpectedly satisfied new required field")
        conn.execute("ALTER TABLE profiles DROP COLUMN full_name")
        conn.execute("INSERT INTO profiles VALUES (1,'Ada')")
        try:
            conn.execute("ALTER TABLE profiles ADD COLUMN full_name text NOT NULL")
        except psycopg.errors.NotNullViolation as error:
            populated_ddl_error = error.sqlstate
        else:
            raise AssertionError("existing NULL values unexpectedly accepted")
        reset(conn)
        return {"old_client_value": old_client, "rename_breaks_old_client": broken,
                "old_write_sqlstate": old_write_error, "populated_ddl_sqlstate": populated_ddl_error}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
docker compose -f infra/e02.compose.yaml up -d --wait
E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[0]' -q
```

完成全部实验后用 `docker compose -f infra/e02.compose.yaml down -v` 清理专用服务。下一步：新增可空字段并声明混合客户端读写策略。
