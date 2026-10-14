# D04 v1：持久化步骤进度并从重启继续

SQLite 记录每个订单步骤状态。进程重启后已完成步骤不重复执行，未完成步骤可以继续。

在 v0 的扣款完成后重启，协调者若只从函数开头重跑，就无法区分库存是否已预留。本版用 `(order_id, name)` 唯一标识一个步骤，把状态从内存移到 SQLite。它不是迁移 v0 的服务数据，而是增加协调者自己的执行记录。

读 `run` 时按三段看：先查询是否已为 `done`；否则提交 `running`，调用外部 `effect`；最后提交 `done`。第一次提交让异常留下可见的未完成记录，第二次提交让后续调用跳过已完成步骤。`status` 只是查询轨迹，不负责自动调度后续步骤。

<!-- checkpoint: labs/coordination/saga/v1.py -->

```python
from __future__ import annotations

import sqlite3


class Saga:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS steps (order_id TEXT, name TEXT, state TEXT, PRIMARY KEY(order_id,name))")
        self.db.commit()

    def completed(self, order: str, name: str) -> bool:
        return self.db.execute("SELECT state='done' FROM steps WHERE order_id=? AND name=?", (order, name)).fetchone() == (1,)

    def run(self, order: str, name: str, effect) -> None:
        if self.completed(order, name):
            return
        self.db.execute("INSERT OR REPLACE INTO steps VALUES (?, ?, 'running')", (order, name))
        self.db.commit()
        effect()
        self.db.execute("UPDATE steps SET state='done' WHERE order_id=? AND name=?", (order, name))
        self.db.commit()

    def status(self, order: str) -> list[tuple[str, str]]:
        return self.db.execute("SELECT name,state FROM steps WHERE order_id=? ORDER BY rowid", (order,)).fetchall()


if __name__ == "__main__":
    saga = Saga(":memory:")
    calls: list[str] = []
    saga.run("order-1", "reserve", lambda: calls.append("reserve"))
    saga.run("order-1", "charge", lambda: calls.append("charge"))
    saga.run("order-1", "reserve", lambda: calls.append("duplicate"))
    print(calls, saga.status("order-1"))
```

## 运行

```bash
uv run python labs/coordination/saga/v1.py
uv run python -m pytest tests/coordination/saga -q
```

脚本输出应为 `['reserve', 'charge'] [('reserve', 'done'), ('charge', 'done')]`，不能出现 `duplicate`。脚本使用 `:memory:`，只演示同一次运行内的跳过；`test_v1_restart_does_not_repeat_done_step` 使用磁盘文件，关闭连接后重开，再确认 reserve 只发生一次。replay 测试检查正文围栏与源码一致并独立执行。

必须区分“done 后重启”和“effect 成功、done 提交前崩溃”：后一种会留下 `running`，重试仍可能重复效果。外部服务需要自己的幂等键，本版不保证 exactly-once。它也没有修复配送失败留下的库存和扣款，下一版为这些已完成效果加入补偿。

