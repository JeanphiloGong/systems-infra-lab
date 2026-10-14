# E02 v1：双客户端发布与独立事件契约

旧、新客户端使用两个真实连接。先以 COALESCE 读取 full_name=NULL 的历史 Ada，然后检查旧 INSERT -> 新读、新双写 -> 旧读、新 INSERT -> 旧读。同一行被新客户端写 Ada Lovelace 后，旧客户端只写 name=Grace；COALESCE 仍读 Ada Lovelace，证明简单 fallback 不安全。迁移窗口 name 是权威字段：新客户端双写，但读取 name；旧写后新读因此得到 Grace。切换 full_name 之前必须排空旧写并最终同步，不能在仍有旧写时切换。事件是另一条契约：old/transition/new 三种 payload 对 old/new 两类 consumer 构成六格矩阵。旧 consumer 拒绝 new-only；新 consumer 暂时接受旧 name；缺两个字段明确拒绝。此函数可以完全不连接数据库运行，SQL 兼容不能替它背书。

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

<!-- checkpoint: labs/dataflows/schema_evolution/v1.py -->

```python
from __future__ import annotations

import json

from common import connect, reset


def read_event(payload: dict[str, str], consumer: str) -> str:
    if consumer == "old":
        return payload["name"]
    return payload["full_name"] if "full_name" in payload else payload["name"]


def event_matrix() -> dict[str, object]:
    messages = {"old": {"name": "Ada"},
                "transition": {"name": "Ada", "full_name": "Ada"},
                "new": {"full_name": "Ada"}}
    results = {}
    for producer, payload in messages.items():
        for consumer in ("old", "new"):
            try:
                results[f"{producer}->{consumer}"] = read_event(payload, consumer)
            except KeyError:
                results[f"{producer}->{consumer}"] = "rejected"
    assert results == {"old->old": "Ada", "old->new": "Ada",
                       "transition->old": "Ada", "transition->new": "Ada",
                       "new->old": "rejected", "new->new": "Ada"}
    for consumer in ("old", "new"):
        try:
            read_event({}, consumer)
        except KeyError:
            continue
        raise AssertionError("missing event name accepted")
    return results


def experiment() -> dict[str, object]:
    with connect() as conn, connect() as old, connect() as new:
        reset(conn)
        conn.execute("CREATE TABLE profiles(id integer PRIMARY KEY, name text NOT NULL)")
        conn.execute("INSERT INTO profiles VALUES (1, 'Ada')")
        conn.execute("ALTER TABLE profiles ADD COLUMN full_name text")
        fallback = new.execute("SELECT COALESCE(full_name,name) FROM profiles WHERE id=1").fetchone()[0]
        old.execute("INSERT INTO profiles(id,name) VALUES (2,'Grace')")
        old_insert_new_read = new.execute("SELECT name FROM profiles WHERE id=2").fetchone()[0]
        new.execute("UPDATE profiles SET name=%s,full_name=%s WHERE id=1", ("Ada Lovelace", "Ada Lovelace"))
        new_write_old_read = old.execute("SELECT name FROM profiles WHERE id=1").fetchone()[0]
        old.execute("UPDATE profiles SET name='Grace' WHERE id=1")
        stale = new.execute("SELECT COALESCE(full_name,name) FROM profiles WHERE id=1").fetchone()[0]
        # During mixed writers, the legacy field is the authoritative read source.
        old_update_new_read = new.execute("SELECT name FROM profiles WHERE id=1").fetchone()[0]
        new.execute("INSERT INTO profiles VALUES (3,'Linus','Linus')")
        new_insert_old_read = old.execute("SELECT name FROM profiles WHERE id=3").fetchone()[0]
        assert (fallback, old_insert_new_read, new_write_old_read, stale, old_update_new_read, new_insert_old_read) == (
            "Ada", "Grace", "Ada Lovelace", "Ada Lovelace", "Grace", "Linus")
        reset(conn)
        return {"fallback": fallback, "old_insert_new_read": old_insert_new_read,
                "new_write_old_read": new_write_old_read, "naive_stale": stale,
                "old_update_new_read": old_update_new_read, "new_insert_old_read": new_insert_old_read,
                "policy": "name authoritative while old writers remain", "additive": True, "dual_write": True,
                "event_matrix": event_matrix()}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

```bash
docker compose -f infra/e02.compose.yaml up -d --wait
E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[1]' -q
```

完成全部实验后用 `docker compose -f infra/e02.compose.yaml down -v` 清理专用服务。下一步：排空旧写后修复不一致字段并可恢复回填。
