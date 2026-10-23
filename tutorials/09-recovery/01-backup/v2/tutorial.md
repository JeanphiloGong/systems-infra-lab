# A01 v2：物理 base backup、WAL 区间连续性和逻辑损坏反例

v1 的逻辑备份只能恢复其快照。要研究之后的时间点，下一步需要整个集群的物理基线与连续 WAL。本版先实际破坏一份逻辑 dump，证明命令失败不能当恢复成功，再生成 base backup 并核查已知 LSN 区间的归档文件。

先按[模块入口](../README.md)启动 A01 专用 PostgreSQL 16.4，并安装同主版本客户端。保留 [v1](../v1/tutorial.md) 的文件。

## 1. 先明确恢复的输入与目标

截断 dump 后使用 pg_restore --exit-on-error --single-transaction 恢复到独立数据库；断言失败且 accounts 不存在，说明失败恢复没有被接纳，也没有污染源表。随后 pg_basebackup -Fp -Xs 复制物理数据目录并带上备份期间必要 WAL；它不是 pg_dump 的另一种输出格式。

## 2. 沿用前版边界，增加当前需要的操作

保留 v1 的 helper，新增 create_base_backup 与 wait_archived_segments。后者把起止 LSN 转成段名，等待区间内每段实际存在且大小为 16 MiB；区间枚举只支持本实验同 timeline、未跨 segment 编号回绕的小区间，不是通用 WAL 校验工具。文件存在与完整大小仍不等于内容可恢复，v3 会启动真正恢复实例。

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

import time

ARCHIVE = Path("/tmp/a01-wal-archive")


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


def create_base_backup(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    command("pg_basebackup", "--dbname=" + DSN, "-D", str(base), "-Fp", "-Xs", "--checkpoint=fast")


def wal_segment_names(start_segment: str, end_segment: str) -> list[str]:
    prefix = start_segment[:8]
    start_number = int(start_segment[8:], 16)
    end_number = int(end_segment[8:], 16)
    if prefix != end_segment[:8] or end_number < start_number:
        raise RuntimeError(f"WAL interval crosses timeline or wraps segment numbering: {start_segment}..{end_segment}")
    return [prefix + f"{number:016X}" for number in range(start_number, end_number + 1)]


def wait_archived_segments(conn: psycopg.Connection, start_lsn: str, end_lsn: str) -> tuple[Path, list[str]]:
    cluster = conn.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0]
    start_segment = conn.execute("SELECT pg_walfile_name(%s::pg_lsn)", (start_lsn,)).fetchone()[0]
    end_segment = conn.execute("SELECT pg_walfile_name(%s::pg_lsn)", (end_lsn,)).fetchone()[0]
    archive = ARCHIVE / cluster
    names = wal_segment_names(start_segment, end_segment)
    conn.execute("SELECT pg_switch_wal()")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if all((archive / name).exists() and (archive / name).stat().st_size == 16777216 for name in names):
            return archive, names
        time.sleep(0.1)
    raise RuntimeError(f"WAL interval not archived: {names}")
```

## 3. 把备份、恢复与数据检查接起来

损坏 dump 的恢复应失败且目标没有 accounts；PG_VERSION 存在，required_wal_segments 非空且每段 16 MiB。此时仍不能宣称 PITR 成功，也没有校验每段内容；下一版由真实恢复进程解释它们。

新建本版完整入口：

<!-- checkpoint: labs/recovery/backup/v2.py -->

```python
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import subprocess

import psycopg

from common import command, connect, create_base_backup, dump, seed, wait_archived_segments, independent_database


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory:
        seed(conn)
        backup = Path(directory) / "accounts.dump"
        dump(backup)
        raw = backup.read_bytes()
        backup.write_bytes(raw[: max(1, len(raw) // 2)])
        with independent_database("damaged") as target_dsn:
            try:
                command("pg_restore", "--exit-on-error", "--single-transaction",
                        "--dbname=" + target_dsn, str(backup))
            except subprocess.CalledProcessError:
                pass
            else:
                raise AssertionError("damaged dump accepted")
            with psycopg.connect(target_dsn) as restored:
                assert restored.execute("SELECT to_regclass('public.accounts')").fetchone()[0] is None
        assert conn.execute("SELECT count(*) FROM accounts").fetchone()[0] == 2
        start_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        conn.execute("INSERT INTO accounts VALUES (3,300)")
        conn.execute("CHECKPOINT")
        end_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        base = Path(directory) / "base"
        create_base_backup(base)
        conn.execute("SELECT pg_switch_wal()")
        archive, segments = wait_archived_segments(conn, start_lsn, end_lsn)
        assert segments and all((archive / segment).stat().st_size == 16777216 for segment in segments)
        return {"corruption_detected": True, "partial_restore_accepted": False,
                "physical_backup": True, "base_backup_complete": (base / "PG_VERSION").exists(),
                "wal_start_lsn": start_lsn, "wal_end_lsn": end_lsn,
                "required_wal_segments": segments, "archive_continuous": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
uv run python labs/recovery/backup/v2.py
```

损坏 dump 的恢复应失败且目标没有 accounts；PG_VERSION 存在，required_wal_segments 非空且每段 16 MiB。此时仍不能宣称 PITR 成功，也没有校验每段内容；下一版由真实恢复进程解释它们。
