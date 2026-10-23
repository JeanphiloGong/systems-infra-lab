# E01 v0：分别写源库和投影会不一致

订单源表和检索投影各写一次。源写成功、投影写失败后，两个存储没有共同提交点。这不是 CDC，先把双写裂缝保留下来。
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

将下面的完整代码保存为 `labs/dataflows/cdc/v0.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/dataflows/cdc/v0.py -->

```python
from __future__ import annotations

import json

from common import connect


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS source_orders, projection")
        conn.execute("CREATE TABLE source_orders(id int PRIMARY KEY, value text)")
        conn.execute("CREATE TABLE projection(id int PRIMARY KEY, value text)")
        conn.execute("INSERT INTO source_orders VALUES (1,'created')")
        try:
            conn.execute("INSERT INTO projection VALUES (1,'created')")
            raise ConnectionError("projection write failed after source write")
        except ConnectionError:
            pass
        assert conn.execute("SELECT count(*) FROM source_orders").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM projection").fetchone()[0] == 1
        conn.execute("DELETE FROM projection")
        return {"source_rows": 1, "projection_rows_after_failure": 0, "inconsistent": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## 运行

```bash
uv run python labs/dataflows/cdc/v0.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/dataflows/cdc -q
```

</details>

正文围栏会被测试提取到空目录，在 E01 专用 PostgreSQL 55450 上执行；R04、共享 PostgreSQL 和内存模拟都不替代这个检查。

