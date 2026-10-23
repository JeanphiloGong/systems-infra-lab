# F01 v2: exhaustion, leaks, and exception-safe return

Pooling introduces a resource that can be exhausted. A borrower that never leaves its context holds a slot indefinitely; another borrower must wait and eventually time out. Context managers make the normal and exceptional paths return the connection.

## Pressure

With `max_size=1`, one forgotten checkout is enough to block every other request. A timeout turns an unbounded wait into an observable failure.

## Naive baseline and break

The unsafe shape is equivalent to:

```python
connection = pool.getconn()
# an exception here skips putconn(connection)
```

The official API deliberately exposes a context manager so application code does not need to remember a separate return call.

## One change: bounded checkout and cleanup

将下面的完整代码保存为 `pool_cleanup.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: pool_cleanup.py -->

```python
from __future__ import annotations

import os

from psycopg_pool import ConnectionPool, PoolTimeout


def main() -> None:
    pool = ConnectionPool(
        os.environ["SYSTEMS_LAB_DATABASE_URL"],
        min_size=0,
        max_size=1,
        timeout=0.2,
        open=True,
    )
    try:
        with pool.connection() as held:
            held.execute("SELECT 1")
            try:
                with pool.connection():
                    raise AssertionError("the second checkout should wait")
            except PoolTimeout:
                print("bounded exhaustion observed")

        try:
            with pool.connection() as connection:
                connection.execute("SELECT 1")
                raise RuntimeError("simulated handler failure")
        except RuntimeError:
            pass

        with pool.connection() as recovered:
            print({"recovered": recovered.execute("SELECT 1").fetchone()[0]})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
```

The timeout is a symptom of a live checkout, not proof of a dead database. The exception path returns the connection and the pool resets it before the next borrower. `pool.close()` belongs in application shutdown; do not close a pool while work still needs to borrow from it.

## Check and freeze

```bash
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv run python pool_cleanup.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/traffic/connections/test_f01_pool.py -q
```

</details>

The tests verify both timeout under an intentional held checkout and recovery after a body exception. The timeout is wall-clock behavior on this local service, not a throughput guarantee.
