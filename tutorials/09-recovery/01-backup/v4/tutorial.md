# A01 v4：成功恢复耗时、失败耗时和数据损失窗口

v3 的成功路径依赖连续归档。本版复制同一套备份做两次恢复：一份保留全部 WAL，一份只在私有副本中删除最后一个必要段。前者必须到达目标，后者必须明确失败；分别测量实际经过的时间。

先按[模块入口](../README.md)启动 A01 专用 PostgreSQL 16.4，并安装同主版本客户端。保留 [v3](../v3/tutorial.md) 的文件。

## 1. 先明确恢复的输入与目标

复制 base 与归档后分别执行 recover_at。成功路径检查恢复暂停且精确读到 1:100,2:100；损坏路径检查 PostgreSQL 日志指出目标尚未到达。用 monotonic 包围实际恢复调用，配置 timeout=5 只是等待上限，不是测得耗时。

## 2. 沿用前版边界，增加当前需要的操作

common.py 沿用 v3。新变化都在 experiment：创建 success-base 与 broken-archive 两份副本，只删除后者的一段，并分别计时。原始归档不被破坏，可以继续用于其他实验。

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

成功与失败路径各自报告实际 elapsed_seconds；两次都可能受机器负载影响，不固定秒数。恢复中缺少 id=3 是显式选择旧目标的结果，不等于本次系统意外丢失一条已确认写。这里展示损失窗口，不能由两条样本推出生产 RPO/RTO。

新建本版完整入口：

<!-- checkpoint: labs/recovery/backup/v4.py -->

```python
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import shutil

from common import connect, create_base_backup, recover_at, seed, wait_archived_segments


def experiment() -> dict[str, object]:
    with connect() as conn, tempfile.TemporaryDirectory() as directory:
        seed(conn)
        base = Path(directory) / "base"
        create_base_backup(base)
        target = conn.execute("SELECT clock_timestamp()::text").fetchone()[0]
        time.sleep(1.1)
        acknowledged_before_target = conn.execute("SELECT count(*) FROM accounts").fetchone()[0]
        start_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        conn.execute("DELETE FROM accounts WHERE id=2")
        conn.execute("INSERT INTO accounts VALUES (3,300)")
        conn.execute("CHECKPOINT")
        end_lsn = conn.execute("SELECT pg_current_wal_insert_lsn()::text").fetchone()[0]
        original, segments = wait_archived_segments(conn, start_lsn, end_lsn)
        success_base = Path(directory) / "success-base"
        shutil.copytree(base, success_base)
        success_started = time.monotonic()
        success_ready, success_rows = recover_at(success_base, target, original)
        success_elapsed = time.monotonic() - success_started
        assert success_ready and success_rows == "1:100,2:100"
        archive = Path(directory) / "broken-archive"
        shutil.copytree(original, archive)
        (archive / segments[-1]).unlink()
        failed_started = time.monotonic()
        ready, output = recover_at(base, target, archive, timeout=5)
        failed_elapsed = time.monotonic() - failed_started
        assert not ready and "recovery ended before configured recovery target was reached" in output, output
        return {"missing_archive_detected": True, "recovery_failed": not ready, "error_excerpt": output[-120:],
                "successful_recovery": True, "recovery_elapsed_seconds": success_elapsed,
                "failed_attempt_elapsed_seconds": failed_elapsed,
                "acknowledged_rows_before_target": acknowledged_before_target,
                "recovered_rows": success_rows, "post_target_rows_not_recovered": 1,
                "data_loss_window": "id=3 committed after target and absent from target recovery",
                "required_wal_segments": segments, "archive_continuous": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
uv run python labs/recovery/backup/v4.py
```

成功与失败路径各自报告实际 elapsed_seconds；两次都可能受机器负载影响，不固定秒数。恢复中缺少 id=3 是显式选择旧目标的结果，不等于本次系统意外丢失一条已确认写。这里展示损失窗口，不能由两条样本推出生产 RPO/RTO。
