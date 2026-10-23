# D04 v4：并发订单与隔离边界

两个订单并发执行时，每个订单的效果键必须隔离且去重。Saga 不提供数据库级隔离；共享库存容量或读取中间状态仍需业务保护。

前面只追踪单个订单。若以 `reserve` 作为全局去重键，订单 a 的成功会错误阻止订单 b；若同一订单的两个线程都先查到记录不存在，又可能重复尝试。这里保留订单 ID 和效果名组成主键，并把查询、插入、提交放到同一个本地 `Lock` 内。

`check_same_thread=False` 允许线程共享连接，但本身不提供互斥，所以仍需锁。`apply` 第一次写入返回 `True`，已存在返回 `False`；`snapshot` 用排序输出便于比较。本版是效果登记表的独立切片，没有把 v3 的补偿循环集成为完整工作流，也没有真正调用库存服务。

将下面的完整代码保存为 `labs/coordination/saga/v4.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/coordination/saga/v4.py -->

```python
from __future__ import annotations

import sqlite3
from threading import Lock


class Orders:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS effects (order_id TEXT, name TEXT, state TEXT, PRIMARY KEY(order_id,name))")
        self.db.commit()
        self.lock = Lock()

    def apply(self, order: str, name: str) -> bool:
        with self.lock:
            row = self.db.execute("SELECT state FROM effects WHERE order_id=? AND name=?", (order, name)).fetchone()
            if row is not None:
                return False
            self.db.execute("INSERT INTO effects VALUES (?, ?, 'done')", (order, name))
            self.db.commit()
            return True

    def snapshot(self) -> list[tuple[str, str, str]]:
        return self.db.execute("SELECT order_id,name,state FROM effects ORDER BY order_id,name").fetchall()


if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    orders = Orders(":memory:")
    start = Barrier(8)

    def attempt(order: str) -> bool:
        start.wait(timeout=5)
        return orders.apply(order, "reserve")

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, ["order-a", "order-b"] * 4))
        assert sum(results) == 2
        assert orders.snapshot() == [("order-a", "reserve", "done"), ("order-b", "reserve", "done")]
        print({"attempts": len(results), "accepted": sum(results), "rows": orders.snapshot()})
    finally:
        orders.db.close()
```

## 运行

```bash
uv run python labs/coordination/saga/v4.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/coordination/saga -q
```

</details>

直接入口用 `Barrier(8)` 把八个线程安排到同一个调用起点，两个订单各提交四次。预期 `attempts=8`、`accepted=2`，最终每单一条记录；具体哪两个线程胜出不固定。线程池结束后再查询，避免把读者检查也混入并发写入。这个检查覆盖同一 `Orders` 实例中的竞争，不代表跨进程或跨数据库隔离。

锁只覆盖共享这个 `Orders` 实例的线程；不同进程或不同连接没有共享它。登记成功也不等于外部业务效果与登记原子提交，不能在返回后直接宣称库存只扣一次。本章冻结的是订单效果键隔离，库存容量约束、跨服务隔离和崩溃窗口仍需真实业务契约解决。

