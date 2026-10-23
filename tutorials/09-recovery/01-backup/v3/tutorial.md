# A01 v3：目标时间恢复误删前数据并验证 WAL 区间

v2 有物理基线与 WAL，但还没证明能找回误删记录。现在在 base backup 完成后记录服务器时间，然后删除 id=2、插入 id=3。恢复实例必须停在误删前，读出 1/2；源库同时仍是 1/3。

先按[模块入口](../README.md)启动 A01 专用 PostgreSQL 16.4，并安装同主版本客户端。保留 [v2](../v2/tutorial.md) 的文件。

## 1. 先明确恢复的输入与目标

目标时间必须晚于 base backup 可恢复的起点，又早于 DELETE 提交。用数据库 clock_timestamp 获取目标，1.1 秒间隔只用于把教学事件时间分开，不作为复制完成判据。再用 LSN 区间等待归档实际落地，而不是睡一会就假定成功。

## 2. 沿用前版边界，增加当前需要的操作

在 v2 上新增 docker 和 recover_at。recover_at 写 recovery.signal 与 recovery_target_time，启动只挂载该 base/归档的恢复容器，通过 docker exec 轮询暂停状态与查询结果；不需要加入其他 Compose 网络。完成后删除恢复容器。目标表结果与源库结果必须分别查询，防止误把源库当恢复库。

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


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("docker", *args), check=check, capture_output=True, text=True)


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


def recover_at(base: Path, target: str, archive: Path, *, timeout: float = 12) -> tuple[bool, str]:
    (archive / "recovery_hba.conf").write_text("local all all trust\nhost all all all trust\n")
    docker("run", "--rm", "-v", f"{base}:/x", "postgres:16.4", "chmod", "-R", "a+rwX", "/x")
    (base / "recovery.signal").write_text("")
    (base / "postgresql.auto.conf").write_text(f"restore_command = 'cp /archive/%f %p'\nrecovery_target_time = '{target}'\n")
    name = "a01-recovery-" + uuid.uuid4().hex[:8]
    started = docker("run", "-d", "--name", name, "--network", "none", "-v", f"{base}:/var/lib/postgresql/data", "-v", f"{archive}:/archive", "postgres:16.4", "postgres", "-D", "/var/lib/postgresql/data", "-c", "hba_file=/archive/recovery_hba.conf", check=False)
    if started.returncode != 0:
        return False, started.stderr
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = docker("exec", name, "pg_isready", "-U", "a01", check=False)
        if result.returncode == 0:
            result = docker("exec", name, "psql", "-U", "a01", "-d", "a01", "-At", "-c", "SELECT string_agg(id::text || ':' || balance::text, ',' ORDER BY id) FROM accounts WHERE pg_get_wal_replay_pause_state() = 'paused'", check=False)
            if result.returncode == 0 and result.stdout.strip():
                docker("rm", "-f", name, check=False)
                docker("run", "--rm", "-v", f"{base}:/x", "postgres:16.4", "chmod", "-R", "a+rwX", "/x")
                return True, result.stdout.strip()
        time.sleep(0.25)
    logs = docker("logs", name, check=False).stderr
    docker("rm", "-f", name, check=False)
    docker("run", "--rm", "-v", f"{base}:/x", "postgres:16.4", "chmod", "-R", "a+rwX", "/x")
    return False, logs
```

## 3. 把备份、恢复与数据检查接起来

恢复目标输出 1:100,2:100，当前源库为 1:100,3:300，且恢复已暂停在目标处。缺 WAL、权限或数据库启动错误都不能算成功。只测本机专用实例，不测跨主机恢复或应用重新接流量。

新建本版完整入口：

<!-- checkpoint: labs/recovery/backup/v3.py -->

```python
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time

from common import connect, create_base_backup, recover_at, seed, wait_archived_segments


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory:
        seed(conn)
        start_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        base = Path(directory) / "base"
        create_base_backup(base)
        target = conn.execute("SELECT clock_timestamp()::text").fetchone()[0]
        time.sleep(1.1)
        conn.execute("DELETE FROM accounts WHERE id=2")
        conn.execute("INSERT INTO accounts VALUES (3,300)")
        conn.execute("CHECKPOINT")
        end_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        archive, segments = wait_archived_segments(conn, start_lsn, end_lsn)
        ready, rows = recover_at(base, target, archive)
        assert ready and rows == "1:100,2:100", rows
        current = conn.execute("SELECT string_agg(id::text || ':' || balance::text, ',' ORDER BY id) FROM accounts").fetchone()[0]
        assert current == "1:100,3:300"
        return {"physical_backup": True, "base_backup_complete": True, "target_rows": rows, "later_rows_absent": True, "deleted_row_restored": True, "current_rows": current,
                "wal_start_lsn": start_lsn, "wal_end_lsn": end_lsn, "required_wal_segments": segments,
                "archive_continuous": all((archive / segment).stat().st_size == 16777216 for segment in segments)}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
uv run python labs/recovery/backup/v3.py
```

恢复目标输出 1:100,2:100，当前源库为 1:100,3:300，且恢复已暂停在目标处。缺 WAL、权限或数据库启动错误都不能算成功。只测本机专用实例，不测跨主机恢复或应用重新接流量。
