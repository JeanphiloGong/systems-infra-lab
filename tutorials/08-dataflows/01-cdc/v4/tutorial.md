# E01 v4：暂停消费者会保留源端 WAL

逻辑 slot 停止消费后，源端 restart_lsn 不能自由前进。批量写入观测 retained bytes 和事件积压；恢复读取后 confirmed_flush_lsn 前进。这个差值不是完整磁盘使用量。
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

<!-- checkpoint: labs/dataflows/cdc/v4.py -->

```python
from __future__ import annotations

import json

from common import connect


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v4_slot"
        conn.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        conn.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        conn.execute("INSERT INTO orders SELECT n, 'paused-' || n FROM generate_series(1,20000) n")
        retained = conn.execute("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)::bigint FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        assert retained > 0
        confirmed_before = conn.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        events = conn.execute("SELECT count(*) FROM pg_logical_slot_get_changes(%s,NULL,NULL)", (slot,)).fetchone()[0]
        conn.execute("CHECKPOINT")
        remaining = conn.execute("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)::bigint FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        confirmed_after = conn.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        assert events > 20000 and confirmed_after >= confirmed_before
        conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))
        return {"rows_written": 20000, "retained_bytes": retained, "events_replayed": events, "remaining_bytes": remaining, "confirmed_advanced": confirmed_after >= confirmed_before, "paused_then_recovered": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## 运行

```bash
uv run python labs/dataflows/cdc/v4.py
uv run python -m pytest tests/dataflows/cdc -q
```

正文围栏会被测试提取到空目录，在 E01 专用 PostgreSQL 55450 上执行；R04、共享 PostgreSQL 和内存模拟都不替代这个检查。

