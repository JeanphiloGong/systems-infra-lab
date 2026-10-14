# D04 v3：补偿失败需要重试和人工状态

补偿本身可能超时。有限重试耗尽后状态变为 manual，系统必须保留待人工处理的事实。

v2 在退款异常时直接退出，协调者既没有尝试次数，也没有可查询的终止原因。本章只研究一项补偿：用 `seed` 放入一个已完成的 reserve 步骤，再让释放库存连续超时。`seed` 是实验准备，不是在重新实现前向 Saga。

每次调用补偿前先把 `attempts` 加一、状态改成 `compensating` 并提交。这样重开同一个数据库文件后能继续使用累计次数；它数的是准备发出的尝试，进程也可能在提交次数后、调用前退出。只捕获 `TimeoutError`：成功写 `compensated`，耗尽上限写 `manual`，其他异常仍传播给调用方。

<!-- checkpoint: labs/coordination/saga/v3.py -->

```python
from __future__ import annotations

import sqlite3


class Saga:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS steps (order_id TEXT, position INTEGER, name TEXT, state TEXT, attempts INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(order_id,position))")
        self.db.commit()

    def seed(self, order: str, position: int, name: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO steps(order_id,position,name,state) VALUES (?, ?, ?, 'done')", (order, position, name))
        self.db.commit()

    def compensate(self, order: str, position: int, effect, max_attempts: int = 3) -> str:
        row = self.db.execute("SELECT state,attempts FROM steps WHERE order_id=? AND position=?", (order, position)).fetchone()
        if row is None or row[0] == "compensated":
            return "already_done"
        attempts = row[1]
        while attempts < max_attempts:
            attempts += 1
            self.db.execute("UPDATE steps SET state='compensating',attempts=? WHERE order_id=? AND position=?", (attempts, order, position))
            self.db.commit()
            try:
                effect(attempts)
            except TimeoutError:
                continue
            self.db.execute("UPDATE steps SET state='compensated' WHERE order_id=? AND position=?", (order, position))
            self.db.commit()
            return "compensated"
        self.db.execute("UPDATE steps SET state='manual' WHERE order_id=? AND position=?", (order, position))
        self.db.commit()
        return "manual"

    def status(self, order: str) -> list[tuple[int, str, str, int]]:
        return self.db.execute("SELECT position,name,state,attempts FROM steps WHERE order_id=? ORDER BY position", (order,)).fetchall()


if __name__ == "__main__":
    saga = Saga(":memory:")
    saga.seed("order-1", 1, "reserve")
    print(saga.compensate("order-1", 1, lambda attempt: (_ for _ in ()).throw(TimeoutError()), max_attempts=2))
    print(saga.status("order-1"))
```

## 运行

```bash
uv run python labs/coordination/saga/v3.py
uv run python -m pytest tests/coordination/saga -q
```

脚本故意令两次调用都超时，第一行必须是 `manual`，第二行为 `[(1, 'reserve', 'manual', 2)]`。`test_v3_timeout_retries_then_manual` 核对这个状态；围栏 replay 则确认正文可独立执行。这条轨迹不表示退款已完成，只表示自动处理已经耗尽两次尝试。

没有退避、人工处理界面或独立恢复 worker；在相同预算下再次处理 manual 不会获得新尝试次数。超时也可能发生在外部效果成功之后，因此接收端幂等仍是前提。下一版单独检查多订单的效果键，防止不同订单互相去重。

