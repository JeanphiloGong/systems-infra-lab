# E01 v2：快照和增量衔接

先创建 slot，再建立明确的快照切点，然后按事务提交顺序应用 INSERT、UPDATE 和 DELETE。只按主键跳过重复 INSERT 会漏掉订单更新、删除和同一主键重新创建。

`snapshot_cut` 在 READ COMMITTED 事务中取得 orders 的 SHARE 表锁，等待已有写事务结束，并阻止新的 INSERT/UPDATE/DELETE 提交。在锁内读取完整快照，再消费此前已经提交的 slot 重叠记录，记录真实 `confirmed_flush_lsn` 作为 `snapshot_cursor`。释放锁后才能发生的写入由 slot 保留，接着顺序应用到快照投影。这里用短暂停写换取直观且可验证的切点；大表或不能停写的系统需要复制协议导出快照等不同方案。

实验先在切点前更新订单，再在切点后同一事务中更新订单 1、删除 3 和 4、重新插入 4、插入 2，最终必须与真实源表完全相同。共享 `order_change` 严格解析固定的 `public.orders(id integer PRIMARY KEY, value text)` 和默认 replica identity：数据值保留空格、双写单引号、反斜杠、换行、空串及 NULL。未知列布局直接报错；这不是任意表的 test_decoding 通用解析器。

测试用两个真实连接证明锁内写入超时、释放后更新出现在增量中。初始化阶段如果进程失败，必须丢弃未完成目标并重做快照；它不是可恢复的分块快照。`get_changes` 第二个参数是读取上界，不是恢复起点。v3 将讨论快照完成后的增量持久恢复。

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

<!-- checkpoint: labs/dataflows/cdc/v2.py -->

```python
from __future__ import annotations

import json

from common import connect, order_change, read_events, snapshot_cut


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v2_slot"
        conn.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        conn.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        try:
            conn.execute("INSERT INTO orders VALUES (1,'before-snapshot'),(3,'remove me'),(4,'old incarnation')")
            conn.execute("UPDATE orders SET value='snapshot updated' WHERE id=1")
            snapshot, cursor = snapshot_cut(conn, slot)
            with conn.transaction():
                conn.execute("UPDATE orders SET value=%s WHERE id=1", ("paid in full; customer's order",))
                conn.execute("DELETE FROM orders WHERE id IN (3,4)")
                conn.execute("INSERT INTO orders VALUES (4,'new incarnation')")
                conn.execute("INSERT INTO orders VALUES (2,'after-snapshot')")
            projection = dict(snapshot)
            events = read_events(conn, slot)
            for event in events:
                change = order_change(event)
                if change is None:
                    continue
                identifier, value = change
                if event.operation == "DELETE":
                    projection.pop(identifier, None)
                else:
                    projection[identifier] = value
            expected = dict(conn.execute("SELECT id,value FROM orders").fetchall())
            assert projection == expected
            assert conn.execute("SELECT %s::pg_lsn > %s::pg_lsn", (events[-1].source_position, cursor)).fetchone()[0]
            return {"snapshot_rows": len(snapshot), "projection": projection, "snapshot_cursor": cursor, "last_source_position": events[-1].source_position, "matches_source": True, "operations": [event.operation for event in events if event.operation != "TRANSACTION"]}
        finally:
            conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## 运行

```bash
uv run python labs/dataflows/cdc/v2.py
uv run python -m pytest tests/dataflows/cdc -q
```

正文围栏会被测试提取到空目录，在 E01 专用 PostgreSQL 55450 上执行；R04、共享 PostgreSQL 和内存模拟都不替代这个检查。

