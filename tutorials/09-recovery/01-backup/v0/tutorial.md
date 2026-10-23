# A01 v0：逻辑备份恢复到独立目标，验证约束并保留源库

你准备修改账户表，想先备份，以便出错后恢复。仅生成 SQL 文件还不算成功：它可能不能导入，或者导入后约束丢失。本版把两条账户记录导出，再恢复到另一个临时数据库，验证数据、主键与 NOT NULL，源库保持原样。

先按[模块入口](../README.md)启动 A01 专用 PostgreSQL 16.4，并安装同主版本客户端。

## 1. 先明确恢复的输入与目标

`pg_dump --format=plain --table=accounts` 读取源库快照，产物是 SQL；`psql --set=ON_ERROR_STOP=1 --file=...` 在独立目标执行这些 SQL。开启 ON_ERROR_STOP 避免中间语句失败却继续到最后。成功退出后仍需查询目标，不能只检查文件存在。

## 2. 准备本版会调用的操作

common.py 只放当前调用需要的操作：connect 连接 A01 源库；seed 建立两条输入；dump/command 调用真实客户端并检查退出码；independent_database 创建随机目标库，在 finally 删除它。后者拥有目标库生命周期，脚本拥有临时 dump 文件。seed 会重建实验源表，因此 DSN 必须指向 A01 专用实例。当前没有 WAL 或物理恢复 helper。

完整替换 `labs/recovery/backup/common.py`：

<!-- checkpoint: labs/recovery/backup/common.py -->

```python
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import uuid
from contextlib import contextmanager

import psycopg
from psycopg.conninfo import make_conninfo, conninfo_to_dict
from psycopg import sql

DSN = os.getenv("A01_DATABASE_URL", "postgresql://a01:a01_local_only@127.0.0.1:55452/a01")


def connect() -> psycopg.Connection:
    return psycopg.connect(DSN, autocommit=True, connect_timeout=3)


@contextmanager
def independent_database(prefix: str):
    admin_dsn = make_conninfo(**{k: v for k, v in conninfo_to_dict(DSN).items() if k != "dbname"}, dbname="postgres")
    name = f"a01_restore_{prefix}_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    target_dsn = make_conninfo(**{k: v for k, v in conninfo_to_dict(DSN).items() if k != "dbname"}, dbname=name)
    try:
        yield target_dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def seed(conn: psycopg.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS accounts")
    conn.execute("CREATE TABLE accounts(id integer PRIMARY KEY, balance integer NOT NULL)")
    conn.execute("INSERT INTO accounts VALUES (1,100),(2,100)")


def command(*args: str) -> None:
    subprocess.run(args, check=True, env={**os.environ, "PGPASSWORD": "a01_local_only"}, capture_output=True, text=True)


def dump(path: Path, fmt: str = "custom") -> None:
    command("pg_dump", "--dbname=" + DSN, "--format=" + fmt, "--file=" + str(path), "--table=accounts")
```

## 3. 把备份、恢复与数据检查接起来

输出 rows_restored=2、source_preserved=true，列约束为 NO/NO；重复主键与 NULL 写入分别返回 SQLSTATE 23505/23502。异常后调用 rollback，才能继续下一次约束检查。成功后临时目标库和 dump 文件被清理。下一版比较备份后的新提交。

新建本版完整入口：

<!-- checkpoint: labs/recovery/backup/v0.py -->

```python
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import psycopg

from common import command, connect, dump, independent_database, seed


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory, independent_database("v0") as target_dsn:
        seed(conn)
        backup = Path(directory) / "accounts.sql"
        dump(backup, "plain")
        command("psql", "--set=ON_ERROR_STOP=1", "--dbname=" + target_dsn, "--file=" + str(backup))
        with connect() as source, psycopg.connect(target_dsn) as restored:
            rows = restored.execute("SELECT * FROM accounts ORDER BY id").fetchall()
            columns = restored.execute("SELECT column_name,is_nullable FROM information_schema.columns WHERE table_name='accounts' ORDER BY ordinal_position").fetchall()
            try:
                restored.execute("INSERT INTO accounts VALUES (1,999)")
            except psycopg.errors.UniqueViolation as error:
                duplicate_sqlstate = error.sqlstate
                restored.rollback()
            try:
                restored.execute("INSERT INTO accounts(id,balance) VALUES (3,NULL)")
            except psycopg.errors.NotNullViolation as error:
                null_sqlstate = error.sqlstate
                restored.rollback()
            assert source.execute("SELECT count(*) FROM accounts").fetchone()[0] == 2
        assert rows == [(1, 100), (2, 100)]
        assert columns == [("id", "NO"), ("balance", "NO")]
        return {"backup": "plain_sql", "rows_restored": len(rows), "round_trip": True,
                "source_preserved": True, "columns": columns,
                "duplicate_sqlstate": duplicate_sqlstate, "null_sqlstate": null_sqlstate}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
uv run python labs/recovery/backup/v0.py
```

输出 rows_restored=2、source_preserved=true，列约束为 NO/NO；重复主键与 NULL 写入分别返回 SQLSTATE 23505/23502。异常后调用 rollback，才能继续下一次约束检查。成功后临时目标库和 dump 文件被清理。下一版比较备份后的新提交。
