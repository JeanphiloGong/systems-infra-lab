# E02 v3：退休门槛、必填约束和最终协议

contract 在同一事务内锁表并检查 migration_clients 中旧协议全部 retired，以及 full_name 无 NULL。实验先证明活跃旧客户端阻止 contraction，再证明退休后仍有 NULL 也阻止；补齐后才设置 NOT NULL、删 name、删 checkpoint 和 client registry。注册表代表受控发布状态，实际环境还需防止退休客户端重新上线。NULL INSERT、省略字段 INSERT、NULL UPDATE 分别必须得到 23502；新协议 Linus 写读成功，旧 SELECT 失败。information_schema 和 to_regclass 检查实际列、约束及过渡表消失。最终 event consumer 只读取 full_name，旧 name-only、缺字段、NULL、空字符串都拒绝；v1 的旧字段 fallback 留在历史版本，不由最终版导入。

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

<!-- checkpoint: labs/dataflows/schema_evolution/v3.py -->

```python
from __future__ import annotations

import json

import psycopg

from common import connect, reset


def contract(conn: psycopg.Connection) -> None:
    with conn.transaction():
        conn.execute("LOCK TABLE profiles, migration_clients IN ACCESS EXCLUSIVE MODE")
        if conn.execute("SELECT count(*) FROM migration_clients WHERE protocol='old' AND active").fetchone()[0]:
            raise RuntimeError("old clients remain")
        if conn.execute("SELECT count(*) FROM profiles WHERE full_name IS NULL").fetchone()[0]:
            raise RuntimeError("backfill incomplete")
        conn.execute("ALTER TABLE profiles ALTER COLUMN full_name SET NOT NULL")
        conn.execute("ALTER TABLE profiles DROP COLUMN name")
        conn.execute("DROP TABLE schema_backfill_checkpoint, migration_clients")


def read_event(payload: dict[str, str]) -> str:
    value = payload["full_name"]
    if not isinstance(value, str) or not value:
        raise ValueError("full_name must be a nonempty string")
    return value


def experiment() -> dict[str, object]:
    with connect() as conn:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL, full_name text)")
        conn.execute("CREATE TABLE migration_clients(protocol text, active boolean)")
        conn.execute("INSERT INTO migration_clients VALUES ('old',true)")
        conn.execute("CREATE TABLE schema_backfill_checkpoint(last_id integer)")
        with conn.cursor() as cursor:
            cursor.executemany("INSERT INTO profiles(id,name,full_name) VALUES (%s,%s,%s)", [(1, "Ada", "Ada"), (2, "Grace", "Grace")])
        try:
            contract(conn)
        except RuntimeError as error:
            assert str(error) == "old clients remain"
        else:
            raise AssertionError("retirement gate bypassed")
        conn.execute("UPDATE migration_clients SET active=false")
        conn.execute("UPDATE profiles SET full_name=NULL WHERE id=2")
        try:
            contract(conn)
        except RuntimeError as error:
            assert str(error) == "backfill incomplete"
        else:
            raise AssertionError("backfill gate bypassed")
        conn.execute("UPDATE profiles SET full_name=name WHERE id=2")
        contract(conn)
        rejected = []
        for statement in ("INSERT INTO profiles(id,full_name) VALUES (3,NULL)",
                          "INSERT INTO profiles(id) VALUES (3)",
                          "UPDATE profiles SET full_name=NULL WHERE id=1"):
            try:
                conn.execute(statement)
            except psycopg.errors.NotNullViolation as error:
                rejected.append(error.sqlstate)
            else:
                raise AssertionError("required field violation accepted")
        conn.execute("INSERT INTO profiles VALUES (3,'Linus')")
        new_read = conn.execute("SELECT full_name FROM profiles ORDER BY id").fetchall()
        try:
            conn.execute("SELECT name FROM profiles")
        except psycopg.errors.UndefinedColumn:
            old_rejected = True
        else:
            old_rejected = False
        assert new_read == [("Ada",), ("Grace",), ("Linus",)] and old_rejected
        columns = conn.execute("SELECT column_name,is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='profiles' ORDER BY ordinal_position").fetchall()
        assert columns == [("id", "NO"), ("full_name", "NO")]
        artifacts = conn.execute("SELECT to_regclass('schema_backfill_checkpoint'),to_regclass('migration_clients')").fetchone()
        assert artifacts == (None, None)
        events = []
        for payload in ({"name": "Ada"}, {}, {"full_name": None}, {"full_name": ""}):
            try:
                read_event(payload)
            except (KeyError, ValueError):
                events.append("rejected")
            else:
                raise AssertionError("final consumer accepted invalid event")
        assert read_event({"full_name": "Linus"}) == "Linus"
        reset(conn)
        return {"new_rows": len(new_read), "not_null": columns[1][1] == "NO",
                "old_client_rejected": old_rejected, "cleanup_complete": artifacts == (None, None),
                "write_rejections": rejected, "retirement_gate": "blocked until retired",
                "event_rejections": events, "final_event": "Linus"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
docker compose -f infra/e02.compose.yaml up -d --wait
E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[3]' -q
```

完成全部实验后用 `docker compose -f infra/e02.compose.yaml down -v` 清理专用服务。下一步：用独立环境验证发布协调和业务客户端退役，不把本实验当作自动部署平台。
