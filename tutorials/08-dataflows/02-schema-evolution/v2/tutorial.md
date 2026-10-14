# E02 v2：最终同步与真实进程回填

本版运行前已排空旧写；实验没有实现部署协调器。新写仍双写，ID 5 的两个字段都是 Protected by new client。为重现 v1 留下的过期 full_name，ID 1 先放 stale old value；迁移准备将不一致值置空，随后按权威 name 回填。主键游标前不得再出现旧写或新增 NULL，否则只扫尾部会漏行。第一批两行数据与游标同事务提交后进程退出 17；第二批提交前退出 19，验证行 3/4 和游标均回滚。恢复 worker 通过 stdout 返回实际处理数 2，重复 worker 返回 0；不使用预填常量。seed/reset 清理实验表和 checkpoint，worker 不 reset。整个实验在同一数据库运行两次，和一个实验内恢复是两项不同检查。

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

<!-- checkpoint: labs/dataflows/schema_evolution/v2.py -->

```python
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from common import connect, reset


def backfill(conn: object, batch_size: int = 2, failpoint: str | None = None) -> tuple[int, int | None]:
    processed = 0
    cursor = conn.execute("SELECT last_id FROM schema_backfill_checkpoint WHERE job=%s", ("profiles_full_name",)).fetchone()[0]
    while True:
        if cursor is None:
            rows = conn.execute("SELECT id,name FROM profiles WHERE full_name IS NULL ORDER BY id LIMIT %s", (batch_size,)).fetchall()
        else:
            rows = conn.execute("SELECT id,name FROM profiles WHERE full_name IS NULL AND id > %s ORDER BY id LIMIT %s", (cursor, batch_size)).fetchall()
        if not rows:
            return processed, cursor
        with conn.transaction():
            for identifier, name in rows:
                conn.execute("UPDATE profiles SET full_name=%s WHERE id=%s AND full_name IS NULL", (name, identifier))
            if failpoint == "before_commit":
                os._exit(19)
            conn.execute("UPDATE schema_backfill_checkpoint SET last_id=%s WHERE job=%s", (rows[-1][0], "profiles_full_name"))
        processed += len(rows)
        cursor = rows[-1][0]
        if failpoint == "after_commit":
            os._exit(17)


def experiment() -> dict[str, object]:
    with connect() as conn:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL, full_name text)")
        conn.execute("CREATE TABLE schema_backfill_checkpoint(job text PRIMARY KEY, last_id integer)")
        conn.execute("INSERT INTO schema_backfill_checkpoint VALUES ('profiles_full_name', NULL)")
        with conn.cursor() as cursor:
            cursor.executemany("INSERT INTO profiles(id,name) VALUES (%s,%s)", [(1, "Ada"), (2, "Grace"), (3, "Linus"), (4, "Margaret"), (5, "Ken")])
        conn.execute("UPDATE profiles SET full_name='Protected by new client' WHERE id=5")
        # The migration starts only after old writers are drained. New writers dual-write.
        conn.execute("UPDATE profiles SET name=full_name WHERE id=5")
        conn.execute("UPDATE profiles SET full_name='stale old value' WHERE id=1")
        # Repair mixed-writer divergence before advancing the NULL-only backfill cursor.
        conn.execute("UPDATE profiles SET full_name=NULL WHERE full_name IS DISTINCT FROM name AND full_name IS NOT NULL")
        script = str(Path(__file__).resolve())
        first = subprocess.run([sys.executable, script, "worker", "after_commit"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert first.returncode == 17
        checkpoint = conn.execute("SELECT last_id FROM schema_backfill_checkpoint WHERE job=%s", ("profiles_full_name",)).fetchone()[0]
        first_batch = conn.execute("SELECT count(*) FROM profiles WHERE id < 5 AND full_name IS NOT NULL").fetchone()[0]
        assert checkpoint == first_batch == 2
        failed = subprocess.run([sys.executable, script, "worker", "before_commit"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert failed.returncode == 19
        assert conn.execute("SELECT last_id FROM schema_backfill_checkpoint WHERE job=%s", ("profiles_full_name",)).fetchone()[0] == checkpoint
        assert conn.execute("SELECT count(*) FROM profiles WHERE id IN (3,4) AND full_name IS NULL").fetchone()[0] == 2
        resumed = subprocess.run([sys.executable, script, "worker", "normal"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert resumed.returncode == 0, resumed.stderr
        repeated = subprocess.run([sys.executable, script, "worker", "normal"], env=os.environ, capture_output=True, text=True, timeout=15)
        assert repeated.returncode == 0, repeated.stderr
        resume_batch, resume_cursor = json.loads(resumed.stdout)
        repeat_batch, repeat_cursor = json.loads(repeated.stdout)
        assert (resume_batch, resume_cursor, repeat_batch, repeat_cursor) == (2, 4, 0, 4)
        remaining = conn.execute("SELECT count(*) FROM profiles WHERE full_name IS NULL").fetchone()[0]
        protected = conn.execute("SELECT full_name FROM profiles WHERE id=5").fetchone()[0]
        assert remaining == 0 and protected == "Protected by new client"
        reset(conn)
        return {"first_batch": first_batch, "checkpoint": checkpoint, "resume_batch": resume_batch, "repeat_batch": repeat_batch, "remaining": remaining, "protected": protected, "process_failure_recovered": True, "uncommitted_batch_rolled_back": True, "fresh_repeat_zero_work": repeat_batch == 0, "resumable": True}


def worker(failpoint: str) -> None:
    with connect() as conn:
        print(json.dumps(backfill(conn, failpoint=None if failpoint == "normal" else failpoint)))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(sys.argv[2])
    else:
        print(json.dumps(experiment()))
```

```bash
docker compose -f infra/e02.compose.yaml up -d --wait
E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[2]' -q
```

完成全部实验后用 `docker compose -f infra/e02.compose.yaml down -v` 清理专用服务。下一步：在旧协议退出和无 NULL 的双重门槛通过后收紧 schema。
