# A01 v1：custom dump 恢复到独立目标，证明备份时点边界

v0 证明了备份可以还原，却没说明它覆盖哪个时间范围。现在生成 custom dump，随后在源库插入第三条记录；目标库恢复后应只有备份时的两条。这个反例说明备份文件不会自动包含之后的提交。

先按[模块入口](../README.md)启动 A01 专用 PostgreSQL 16.4，并安装同主版本客户端。保留 [v0](../v0/tutorial.md) 的文件。

## 1. 先明确恢复的输入与目标

把 dump 的格式从 plain 改为 custom，恢复命令相应改为 pg_restore；它不是可直接交给 psql 的 SQL 文件。先 dump，再 INSERT，再 restore，三个动作顺序固定，因此“第三条不出现”是可重复的快照边界，不依赖随机时间。

## 2. 沿用前版边界，增加当前需要的操作

沿用 v0 的五个 helper，不增加 PITR 逻辑。dump 默认 custom，v0 仍可显式传 plain。independent_database 继续负责隔离目标，备份后源库的新增记录不会被恢复流程删除。

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

目标为 [(1,100),(2,100)]，源为 [(1,100),(2,100),(3,50)]。post_backup_row_excluded=true 只说明这次备份的快照边界；不提供按任意时间恢复。下一版准备物理基线和归档。

新建本版完整入口：

<!-- checkpoint: labs/recovery/backup/v1.py -->

```python
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import psycopg

from common import command, connect, dump, independent_database, seed


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory, independent_database("v1") as target_dsn:
        seed(conn)
        backup = Path(directory) / "accounts.dump"
        dump(backup)
        conn.execute("INSERT INTO accounts VALUES (3,50)")
        command("pg_restore", "--exit-on-error", "--dbname=" + target_dsn, str(backup))
        with connect() as source, psycopg.connect(target_dsn) as restored:
            rows = restored.execute("SELECT * FROM accounts ORDER BY id").fetchall()
            source_rows = source.execute("SELECT * FROM accounts ORDER BY id").fetchall()
        assert rows == [(1, 100), (2, 100)]
        assert source_rows == [(1, 100), (2, 100), (3, 50)]
        return {"backup": "custom_format", "rows_at_backup": len(rows), "post_backup_row_excluded": True, "source_preserved": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
uv run python labs/recovery/backup/v1.py
```

目标为 [(1,100),(2,100)]，源为 [(1,100),(2,100),(3,50)]。post_backup_row_excluded=true 只说明这次备份的快照边界；不提供按任意时间恢复。下一版准备物理基线和归档。
