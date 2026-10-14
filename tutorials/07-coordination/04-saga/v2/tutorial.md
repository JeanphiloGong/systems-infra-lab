# D04 v2：逆序补偿是业务操作

配送失败后按逆序退款和释放库存。补偿写入持久状态并且可重复调用，不把它称作数据库回滚。

v1 能知道 reserve 和 charge 已完成，却不能让失败订单回到可接受的业务状态。现在给步骤加 `position`：1 是预留，2 是扣款。调用方先补偿 2 再补偿 1，分别执行退款和释放库存；代码里的 `compensate` 不会自己遍历或排序，这个逆序由下面的调用顺序保证。

一次补偿先检查记录是否存在、是否已为 `compensated`，然后调用业务动作，最后提交补偿状态。再次调用已完成补偿会直接返回。退款不是擦除扣款的历史，也无法撤回其他服务已经读到的中间状态，所以它与数据库回滚有不同契约。

<!-- checkpoint: labs/coordination/saga/v2.py -->

```python
from __future__ import annotations

import sqlite3


class Saga:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS steps (order_id TEXT, position INTEGER, name TEXT, state TEXT, PRIMARY KEY(order_id,position))")
        self.db.commit()

    def step(self, order: str, position: int, name: str, effect) -> None:
        row = self.db.execute("SELECT state FROM steps WHERE order_id=? AND position=?", (order, position)).fetchone()
        if row and row[0] == "done":
            return
        self.db.execute("INSERT OR REPLACE INTO steps VALUES (?, ?, ?, 'running')", (order, position, name))
        self.db.commit()
        effect()
        self.db.execute("UPDATE steps SET state='done' WHERE order_id=? AND position=?", (order, position))
        self.db.commit()

    def compensate(self, order: str, position: int, effect) -> None:
        row = self.db.execute("SELECT state FROM steps WHERE order_id=? AND position=?", (order, position)).fetchone()
        if row is None or row[0] == "compensated":
            return
        effect()
        self.db.execute("UPDATE steps SET state='compensated' WHERE order_id=? AND position=?", (order, position))
        self.db.commit()

    def status(self, order: str) -> list[tuple[int, str, str]]:
        return self.db.execute("SELECT position,name,state FROM steps WHERE order_id=? ORDER BY position", (order,)).fetchall()


if __name__ == "__main__":
    saga = Saga(":memory:")
    effects: list[str] = []
    saga.step("order-1", 1, "reserve", lambda: effects.append("reserved"))
    saga.step("order-1", 2, "charge", lambda: effects.append("charged"))
    saga.compensate("order-1", 2, lambda: effects.append("refunded"))
    saga.compensate("order-1", 1, lambda: effects.append("released"))
    saga.compensate("order-1", 1, lambda: effects.append("duplicate-release"))
    print(effects, saga.status("order-1"))
```

## 运行

```bash
uv run python labs/coordination/saga/v2.py
uv run python -m pytest tests/coordination/saga -q
```

脚本的效果列表必须为 `['reserved', 'charged', 'refunded', 'released']`，两条步骤记录最终均为 `compensated`，不能出现 `duplicate-release`。`test_v2_reverse_compensation_is_idempotent` 验证这条轨迹；replay 测试逐字核对并独立执行正文源码。

这只对补偿状态已提交后的再次调用去重；业务补偿成功而状态提交前崩溃，仍可能重复退款。调用者还必须决定哪些步骤值得补偿：当前函数除缺失/已补偿外也接受 `running`，不能推断它只会补偿成功步骤。下一版研究补偿超时的处理，而不是把超时当作已撤销。

