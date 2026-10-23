# E01 v3：目标投影和消费位置同事务提交

用 SQLite 目标表与 checkpoint 表同一事务写入。重放同一 LSN 时 INSERT OR REPLACE/IGNORE 使目标效果和消费位置幂等；外部系统若不支持事务仍需要它自己的幂等键。

checkpoint 保存这批事务末尾事件的真实 `source_position`、`event_key` 和批次内 `version`，没有用订单 ID 代替源位置。每个新 worker 先用 `peek_changes` 读取而不确认，SQLite 文件事务提交后才用 `get_changes` 确认到本批末尾 LSN。上界不可省略，否则读取后新到达的事务也可能被提前确认。

父进程创建临时磁盘上的 SQLite 文件和真实源变更，然后依次启动三个独立 worker：第一个在目标提交前直接退出，重开文件应没有投影和 checkpoint；第二个在目标提交后、源确认前退出，文件中应同时存在投影和真实源位置；第三个重新从 slot 读取同一事件并幂等重放，再确认源位置。每次故障后源 LSN、事件身份和未确认位置必须不变。worker 不接收父进程的事件列表，恢复依赖磁盘和 PostgreSQL。

快照使用 v2 相同的停写切点，初始化到磁盘后开始增量故障实验。增量含 UPDATE、DELETE、删除后重新 INSERT 和新 INSERT，worker 使用同一个严格字段解码器，按源提交顺序执行 upsert/delete。提交前崩溃必须保留原快照；提交后崩溃和恢复必须得到与真实源表相同的结果。初始化未完成时需要重新建立快照，不能拿半完成快照继续消费。

本例只有一个消费者和固定 orders 表结构。SQLite 文件在实验结束时删除；长期运行需持久目标和 slot 运维。它验证进程故障下的数据库事务边界，不声称任意外部业务副作用都能端到端 exactly-once。

将下面的完整代码保存为 `labs/dataflows/cdc/common.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/dataflows/cdc/common.py -->

```python
from __future__ import annotations

import psycopg
from dataclasses import dataclass
import re


DSN = "postgresql://e01:e01_local_only@127.0.0.1:55450/e01"


def connect() -> psycopg.Connection:
    return psycopg.connect(DSN, autocommit=True, connect_timeout=3)


def cleanup(conn: psycopg.Connection, slot: str) -> None:
    conn.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
    conn.execute("DROP TABLE IF EXISTS orders")
    conn.execute("DROP TABLE IF EXISTS projection")


@dataclass(frozen=True)
class Event:
    key: str
    version: int
    source_position: str
    xid: int
    operation: str
    data: str


def read_events(conn: psycopg.Connection, slot: str, *, consume: bool = True) -> list[Event]:
    query = "SELECT lsn, xid, data FROM pg_logical_slot_get_changes(%s, NULL, NULL)" if consume else "SELECT lsn, xid, data FROM pg_logical_slot_peek_changes(%s, NULL, NULL)"
    rows = conn.execute(query, (slot,)).fetchall()
    events: list[Event] = []
    for version, (position, xid, data) in enumerate(rows, start=1):
        operation = next((candidate for candidate in ("INSERT", "UPDATE", "DELETE") if f": {candidate}:" in data), "TRANSACTION")
        events.append(Event(f"{xid}:{position}:{operation}", version, str(position), xid, operation, data))
    return events


def order_change(event: Event) -> tuple[int, str | None] | None:
    if event.operation == "TRANSACTION":
        return None
    match = re.fullmatch(r"table public\.orders: (INSERT|UPDATE|DELETE): id\[integer\]:(-?\d+)(?: value\[text\]:(null|'(?:[^']|'')*'))?", event.data, re.S)
    if match is None or match[1] != event.operation:
        raise ValueError(f"unsupported orders decoding record: {event.data!r}")
    raw = match[3]
    if (event.operation == "DELETE") != (raw is None):
        raise ValueError("unexpected orders column layout")
    value = None if raw is None or raw == "null" else raw[1:-1].replace("''", "'")
    return int(match[2]), value


def snapshot_cut(conn: psycopg.Connection, slot: str) -> tuple[list[tuple[int, str | None]], str]:
    with conn.transaction():
        conn.execute("LOCK TABLE orders IN SHARE MODE")
        rows = conn.execute("SELECT id,value FROM orders ORDER BY id").fetchall()
        # Writers cannot commit changes while we discard the snapshot overlap.
        read_events(conn, slot)
        cursor = str(conn.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0])
    return rows, cursor
```

将下面的完整代码保存为 `labs/dataflows/cdc/v3.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/dataflows/cdc/v3.py -->

```python
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import connect, order_change, read_events, snapshot_cut


def worker(database: str, slot: str, failpoint: str) -> None:
    with connect() as source, sqlite3.connect(database) as target:
        events = read_events(source, slot, consume=False)
        assert events
        last = events[-1]
        with target:
            for event in events:
                change = order_change(event)
                if change is None:
                    continue
                identifier, value = change
                if event.operation == "DELETE":
                    target.execute("DELETE FROM projection WHERE id=?", (identifier,))
                else:
                    target.execute("INSERT OR REPLACE INTO projection VALUES (?, ?)", (identifier, value))
            target.execute("INSERT OR IGNORE INTO checkpoint VALUES (?, ?, ?)", (last.source_position, last.key, last.version))
            if failpoint == "before_commit":
                os._exit(17)
        if failpoint == "after_commit":
            os._exit(18)
        # Acknowledge only the committed batch, never later concurrent writes.
        source.execute("SELECT count(*) FROM pg_logical_slot_get_changes(%s, %s::pg_lsn, NULL)", (slot, last.source_position)).fetchone()


def experiment() -> dict[str, object]:
    with TemporaryDirectory() as directory, connect() as source:
        database = str(Path(directory) / "projection.sqlite")
        with sqlite3.connect(database) as target:
            target.execute("CREATE TABLE projection(id INTEGER PRIMARY KEY, value TEXT)")
            target.execute("CREATE TABLE checkpoint(source_position TEXT PRIMARY KEY, event_key TEXT NOT NULL, version INTEGER NOT NULL)")
        source.execute("DROP TABLE IF EXISTS orders")
        source.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v3_slot"
        source.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        source.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        source.execute("INSERT INTO orders VALUES (1,'before-snapshot'),(3,'remove me'),(4,'old incarnation')")
        snapshot, cursor = snapshot_cut(source, slot)
        with sqlite3.connect(database) as target:
            target.executemany("INSERT INTO projection VALUES (?, ?)", snapshot)
        with source.transaction():
            source.execute("UPDATE orders SET value=%s WHERE id=1", ("paid in full; customer's order",))
            source.execute("DELETE FROM orders WHERE id IN (3,4)")
            source.execute("INSERT INTO orders VALUES (4,'new incarnation')")
            source.execute("INSERT INTO orders VALUES (2,'after-snapshot')")
        source_rows = source.execute("SELECT id,value FROM orders ORDER BY id").fetchall()
        expected = read_events(source, slot, consume=False)
        confirmed = source.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        try:
            for failpoint, expected_exit in (("before_commit", 17), ("after_commit", 18), ("recover", 0)):
                result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "worker", database, slot, failpoint], capture_output=True, text=True, timeout=15)
                assert result.returncode == expected_exit, result.stderr
                with sqlite3.connect(database) as target:
                    projection = target.execute("SELECT * FROM projection ORDER BY id").fetchall()
                    checkpoints = target.execute("SELECT * FROM checkpoint").fetchall()
                if failpoint == "before_commit":
                    assert projection == snapshot and checkpoints == []
                else:
                    assert projection == source_rows
                    assert checkpoints == [(expected[-1].source_position, expected[-1].key, expected[-1].version)]
                if failpoint != "recover":
                    assert read_events(source, slot, consume=False) == expected
                    assert source.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0] == confirmed
            assert read_events(source, slot, consume=False) == []
            advanced = source.execute("SELECT confirmed_flush_lsn > %s::pg_lsn FROM pg_replication_slots WHERE slot_name=%s", (confirmed, slot)).fetchone()[0]
            assert advanced
            return {"projection": projection, "checkpoints": len(checkpoints), "source_position": checkpoints[0][0], "event_key": checkpoints[0][1], "version": checkpoints[0][2], "replay_safe": True, "crash_before_commit_rolled_back": True, "crash_after_commit_replayed": True, "fresh_processes": 3, "source_ack_after_commit": advanced}
        finally:
            source.execute("SELECT pg_drop_replication_slot(%s)", (slot,))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(*sys.argv[2:])
    else:
        print(json.dumps(experiment()))
```

## 运行

```bash
uv run python labs/dataflows/cdc/v3.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/dataflows/cdc -q
```

</details>

正文围栏会被测试提取到空目录，在 E01 专用 PostgreSQL 55450 上执行；R04、共享 PostgreSQL 和内存模拟都不替代这个检查。

