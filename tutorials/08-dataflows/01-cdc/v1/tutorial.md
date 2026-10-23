# E01 v1：从已提交 WAL 变更读取 CDC

PostgreSQL logical slot 使用 test_decoding 捕获已提交 INSERT/UPDATE/DELETE。每条结果带 WAL LSN 和文本事件；事件顺序是这个 slot 的读取顺序，不是所有表的全局业务顺序。

`Event.source_position` 原样保留 PostgreSQL 返回的 LSN，例如 `0/163AB90`；它不是 Python 计数器。`xid` 是源事务 ID，`key` 由 xid、LSN、操作类型组成，作为这个单一 slot 实验的事件身份，不是订单主键。`version` 只表示本次读取批次中的序号，每次读取从 1 开始，不能当成跨批次的业务版本或恢复游标。

BEGIN、数据行与 COMMIT 都保留在结果中，事务边界和数据行可以共享 LSN，所以整个流只要求位置不倒退；本例三个数据变更的位置互不相同。比较 LSN 时按 PostgreSQL `pg_lsn` 或高低两段十六进制数值比较，不能按字符串排序。这个结构化事件只解析操作类型，仍保留原始文本；生产连接器需要正式的消息格式和来源标识。

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

将下面的完整代码保存为 `labs/dataflows/cdc/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/dataflows/cdc/v1.py -->

```python
from __future__ import annotations

import json
from common import connect, read_events


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v1_slot"
        conn.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        conn.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        conn.execute("INSERT INTO orders VALUES (1,'created')")
        conn.execute("UPDATE orders SET value='paid' WHERE id=1")
        conn.execute("DELETE FROM orders WHERE id=1")
        events = read_events(conn, slot)
        data_events = [event for event in events if event.operation != "TRANSACTION"]
        assert len(data_events) == 3
        assert len({event.source_position for event in data_events}) == len(data_events)
        assert [event.version for event in events] == list(range(1, len(events) + 1))
        conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))
        return {"event_count": len(events), "data_event_count": len(data_events), "contains_insert": any(event.operation == "INSERT" for event in data_events), "contains_update": any(event.operation == "UPDATE" for event in data_events), "contains_delete": any(event.operation == "DELETE" for event in data_events), "source_positions": [event.source_position for event in events], "event_keys": [event.key for event in data_events], "versions": [event.version for event in events], "data_positions": [event.source_position for event in data_events], "xids": [event.xid for event in data_events], "operations": [event.operation for event in data_events], "source": "test_decoding"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## 运行

```bash
uv run python labs/dataflows/cdc/v1.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/dataflows/cdc -q
```

</details>

正文围栏会被测试提取到空目录，在 E01 专用 PostgreSQL 55450 上执行；R04、共享 PostgreSQL 和内存模拟都不替代这个检查。

