# T03 v3：相反锁顺序形成等待环

前置v2。一个订单要同时扣两个商品，另一个订单恰好反向访问；只拥有行锁不代表不会死锁。保持v1的schema.sql，在入口初始化后增加INSERT INTO inventory VALUES (2,10,0)，这是第二资源首次出现。

## 1. 先制造确定的环

两个线程分别先锁1和2，在Barrier(2)会合后才请求另一行。此时各自持有对方需要的锁，PostgreSQL检测等待环并以DeadlockDetected（40P01）中止一个事务。受害者不固定，所以测试只断言恰好一个失败，不断言哪个线程失败。Barrier有超时；不使用sleep。

decrement_pair用一个事务包住两次扣减，捕获异常的位置在事务块外，确保失败方此前扣减已经回滚。库存不足用ValueError向调用者传播，不把业务失败冒充死锁。

## 2. 重试与消除该等待环

主线程收集两边结果，失败者重新执行整个事务，固定按(1,2)加锁。预期一名受害者、两行都为8；如果只重试失败SQL，先前事务已回滚，会漏掉第一次扣减。

再把两行重置为10，两工作线程都按(1,2)锁定。此时不在首锁后放Barrier，否则第二方拿不到首锁就会让屏障僵住。固定全局顺序消除这个两资源环，但不等于数据库再无任何死锁。ordered是对照调用者，复用decrement_pair，失败明确抛出。

## 3. 完整检查点与验证

沿用v1的schema.sql及v0的环境，所有命令在仓库根目录运行。下面完整新建 `labs/transactions/locking/deadlock.py`，代码包含上述机制及完整调用入口。

<!-- checkpoint: labs/transactions/locking/deadlock.py -->

```python
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import os
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg import sql


def decrement_pair(conn: psycopg.Connection, order: tuple[int, int], barrier: Barrier | None = None) -> bool:
    try:
        with conn.transaction():
            for index, item in enumerate(order):
                quantity = conn.execute("SELECT quantity FROM inventory WHERE id=%s FOR UPDATE", (item,)).fetchone()[0]
                if index == 0 and barrier is not None:
                    barrier.wait(timeout=5)
                if quantity <= 0:
                    raise ValueError("insufficient stock")
                conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=%s", (item,))
        return True
    except psycopg.errors.DeadlockDetected:
        return False


def deadlock(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int, int]:
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(decrement_pair, first, (1, 2), barrier)
        b = pool.submit(decrement_pair, second, (2, 1), barrier)
        outcomes = [a.result(timeout=12), b.result(timeout=12)]
    if sum(outcomes) != 1:
        raise AssertionError("expected exactly one deadlock victim")
    loser = first if not outcomes[0] else second
    if not decrement_pair(loser, (1, 2)):
        raise AssertionError("ordered retry failed")
    quantities = first.execute("SELECT quantity FROM inventory ORDER BY id").fetchall()
    return outcomes.count(False), quantities[0][0], quantities[1][0]


def ordered(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(decrement_pair, first, (1, 2))
        b = pool.submit(decrement_pair, second, (1, 2))
        if not a.result(timeout=12) or not b.result(timeout=12):
            raise AssertionError("ordered run deadlocked")
    values = first.execute("SELECT quantity FROM inventory ORDER BY id").fetchall()
    return values[0][0], values[1][0]


def main() -> None:
    with ExitStack() as stack:
        connections = [stack.enter_context(psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True)) for _ in range(2)]
        first = connections[0]
        schema = "t03_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in connections:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            first.execute("INSERT INTO inventory VALUES (2,10,0)")
            print("victims and retried quantities:", deadlock(*connections))
            first.execute("UPDATE inventory SET quantity=10")
            print("ordered quantities:", ordered(*connections))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.locking.deadlock
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/transactions/locking/test_t03_deadlock.py -q
```

</details>

输出victims and retried quantities: (1,8,8)，ordered quantities: (8,8)（Python显示逗号后空格）。下一版离开真实库，专门观察锁记录合并的代价。
