# E03 v1：事件流成为事实来源

一个订单的事件按流版本追加，重放器从 new 开始应用有限状态转换。非法的 shipped -> paid 必须拒绝，否则历史损坏会被静默接受。

## Complete Checkpoint

将下面的完整代码保存为 `labs/dataflows/events/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/dataflows/events/v1.py -->

```python
"""Append immutable domain events and replay a deterministic order state."""
from __future__ import annotations

import json
import sqlite3


class EventStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (stream TEXT, version INTEGER, kind TEXT, payload TEXT, PRIMARY KEY(stream, version))")
        self.db.commit()

    def append(self, stream, kind, payload):
        version = self.db.execute("SELECT coalesce(max(version),0)+1 FROM events WHERE stream=?", (stream,)).fetchone()[0]
        self.db.execute("INSERT INTO events VALUES (?,?,?,?)", (stream, version, kind, json.dumps(payload, sort_keys=True)))
        self.db.commit()
        return version

    def read(self, stream):
        return [(version, kind, json.loads(payload)) for version, kind, payload in self.db.execute("SELECT version,kind,payload FROM events WHERE stream=? ORDER BY version", (stream,))]


def replay(events):
    state = "new"
    allowed = {"new": {"OrderPlaced": "placed"}, "placed": {"OrderPaid": "paid", "OrderCancelled": "cancelled"}, "paid": {"OrderShipped": "shipped"}, "shipped": {}, "cancelled": {}}
    for _, kind, _ in events:
        if kind not in allowed[state]:
            raise ValueError(f"invalid transition {state}->{kind}")
        state = allowed[state][kind]
    return state


def experiment():
    store = EventStore()
    for kind in ("OrderPlaced", "OrderPaid", "OrderShipped"):
        store.append("order-1", kind, {})
    events = store.read("order-1")
    assert [version for version, _, _ in events] == [1, 2, 3] and replay(events) == "shipped"
    try:
        replay([(1, "OrderShipped", {})])
    except ValueError:
        invalid_rejected = True
    else:
        invalid_rejected = False
    assert invalid_rejected
    return {"versions": [v for v, _, _ in events], "state": replay(events), "invalid_rejected": invalid_rejected}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## Run And Verify

```bash
uv run python labs/dataflows/events/v1.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/dataflows/events -q
```

</details>

The assertions check this version's behavior. The replay test writes this fence into a fresh temporary directory and runs a new interpreter without hidden repository imports.

EventStore 使用 SQLite PRIMARY KEY(stream,version)，read 按版本排序；replay 只改变内存状态，不发送副作用。

This is a single SQLite teaching model. It does not provide cross-service transactions, global event ordering, distributed projection coordination or CDC. Event Sourcing treats domain events as facts; it is not change capture from an existing table.

