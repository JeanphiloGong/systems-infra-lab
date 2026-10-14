# T03 v2：读取期间持有行锁

v1通过版本条件拒绝旧写入；高争用下调用者可能反复失败。现在让竞争者等待，等持锁者完成后再读取新值。模型只有一行库存，两个工作连接和一个只观察锁等待的连接。

## 1. 从覆盖写入改为受锁保护的读取

关键变化是把SELECT quantity FOR UPDATE与UPDATE放在同一事务里。只锁SELECT然后立刻提交没有用。持锁者读10并持有锁，第二个连接的SELECT必须等它提交；在READ COMMITTED下醒来后读9，再减到8。

为了验证确实等待，不能用sleep猜测。工作线程先发出Event表示即将执行查询，观察连接查询pg_blocking_pids，直到确认owner的PID在waiter的阻塞列表里，主线程才提交。循环有5秒截止时间，连接另设8秒statement_timeout；这些只是失败上限，不用于制造调度。

## 2. 记录代价

waited测量第二次SELECT开始到返回，held测量首个锁获取后到提交前；它们包含调度和SQL开销，不是纯锁服务耗时。实验是一次机制观察，不是性能基准，也不能宣称某个固定百分比更快。乐观版本遇到一次旧版本失败，这里两次扣减都完成但第二次等待。

函数新增的decrement只为线程执行第二个事务；输入为本实验专用连接。ThreadPool退出发生在owner事务退出之后，异常时owner也会回滚释放锁，避免主线程持锁等待线程退出。

## 3. 完整检查点与验证

沿用v1的schema.sql及v0的环境，所有命令在仓库根目录运行。下面完整新建 `labs/transactions/locking/row_lock.py`，代码包含上述机制及完整调用入口。

<!-- checkpoint: labs/transactions/locking/row_lock.py -->

```python
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import os
from pathlib import Path
from threading import Event
from time import monotonic
from uuid import uuid4

import psycopg
from psycopg import sql


def row_lock(owner: psycopg.Connection, waiter: psycopg.Connection, observer: psycopg.Connection) -> tuple[int, float, float]:
    """Use fresh autocommit connections sharing the initialized inventory schema."""
    entered = Event()

    def decrement() -> float:
        with waiter.transaction():
            waiter.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            entered.set()
            start = monotonic()
            quantity = waiter.execute("SELECT quantity FROM inventory WHERE id=1 FOR UPDATE").fetchone()[0]
            waited = monotonic() - start
            if quantity > 0:
                waiter.execute("UPDATE inventory SET quantity=%s WHERE id=1", (quantity - 1,))
        return waited

    with ThreadPoolExecutor(max_workers=1) as pool:
        with owner.transaction():
            quantity = owner.execute("SELECT quantity FROM inventory WHERE id=1 FOR UPDATE").fetchone()[0]
            held_start = monotonic()
            future = pool.submit(decrement)
            if not entered.wait(timeout=5):
                raise TimeoutError("waiter never entered")
            deadline = monotonic() + 5
            while True:
                blockers = observer.execute("SELECT pg_blocking_pids(%s)", (waiter.info.backend_pid,)).fetchone()[0]
                if owner.info.backend_pid in blockers:
                    break
                if monotonic() >= deadline:
                    raise TimeoutError("waiter never blocked on owner")
            if quantity > 0:
                owner.execute("UPDATE inventory SET quantity=%s WHERE id=1", (quantity - 1,))
            held = monotonic() - held_start
        waited = future.result(timeout=5)
    final = observer.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]
    return final, waited, held


def main() -> None:
    with ExitStack() as stack:
        connections = [stack.enter_context(psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True)) for _ in range(3)]
        owner = connections[0]
        schema = "t03_" + uuid4().hex
        owner.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in connections:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            owner.execute(Path(__file__).with_name("schema.sql").read_text())
            final, waited, held = row_lock(*connections)
            print(f"quantity={final} wait_seconds={waited:.6f} hold_seconds={held:.6f}")
        finally:
            owner.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.locking.row_lock
uv run python -m pytest tests/transactions/locking/test_t03_row_lock.py -q
```

数量应为8，wait_seconds和hold_seconds是本次测量，不断言固定数值。测试必须真实观察锁等待。下一版引入第二行，使等待能形成环。
