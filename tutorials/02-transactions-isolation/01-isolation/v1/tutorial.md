# T01 v1：另一个连接能看到未提交的扣款吗？

v0 保证失败转账回滚，但用户的余额页面由另一个连接查询。在扣款完成、回滚尚未发生的短暂窗口里，它会不会显示 70？我们保留 v0 的两行数据，只增加一个观察连接。目标不是实现隔离机制，而是建立可复现的证据。

前置为 [v0](../v0/tutorial.md)，沿用其 `schema.sql`、uv 环境及临时 PostgreSQL。两个连接都设置 autocommit=True，显式事务块控制边界。每次命令使用新 schema，避免上次实验影响结果。

## 1. 先明确执行顺序

以前只有“UPDATE → 异常 → SELECT”，读取已经在回滚之后，无法回答窗口内是否可见。我们需要下面这个次序：

```text
writer BEGIN
writer UPDATE A=70
writer SELECT A        # 自己读到什么？
reader SELECT A        # writer 尚未提交
writer ROLLBACK
reader SELECT A
```

同步 Python 可以逐条发出这些命令：事务在服务器上保持打开，两个事务的生命周期重叠。不需要线程，也不需要等待随机碰撞。普通 SELECT 在这里读取可见版本，不是 SELECT FOR UPDATE。

新建 `labs/transactions/isolation/observations.py`，先定义 `dirty_read(writer, reader, level)`，使用两个真实连接。`writer.transaction(force_rollback=True)` 保证正常离开也回滚，让扣款始终是未提交尝试。reader 的事务块必须在第一条查询之前执行 `SET TRANSACTION ISOLATION LEVEL`。

先在 `observations.py` 保存这个完整函数 checkpoint：

```python
import psycopg
from psycopg import sql


def dirty_read(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "READ UNCOMMITTED"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        with writer.transaction(force_rollback=True):
            writer.execute("UPDATE accounts SET balance=70 WHERE id=1")
            own = writer.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
            other = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
        after = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
    return own, other, after
```

将下面完整检查程序保存到仓库根目录的临时 `check_t01.py`，执行 `uv run python check_t01.py`。初始化沿用 v0 的 SQL 文件；finally 只删除本程序创建的 schema，这份程序是临时检查；后续若要复用，重新从本节代码块创建即可。

```python
import os
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from labs.transactions.isolation.observations import dirty_read

dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
with psycopg.connect(dsn, autocommit=True) as writer, psycopg.connect(dsn, autocommit=True) as reader:
    schema = "t01_" + uuid4().hex
    writer.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        for conn in (writer, reader):
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        writer.execute(Path("labs/transactions/isolation/schema.sql").read_text())
        result = dirty_read(writer, reader, "READ COMMITTED")
        assert result == (70, 100, 100)
        print(result)
    finally:
        writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
```

预期 `(70, 100, 100)`：自己看到写入不叫脏读；脏读指另一个事务读到未提交数据。此时冻结这个事件次序，下一步只改变隔离级别。

## 2. 名称叫 READ UNCOMMITTED，会改变结果吗？

把检查程序的调用参数改为 `"READ UNCOMMITTED"`，这是实验配置 patch，SQL 和事件次序保持不变。重新运行，预期仍为 `(70, 100, 100)`。

PostgreSQL 接受这个隔离级别名称，但按 READ COMMITTED 的语义执行，所以本库无法用它复现脏读。不要为了凑齐术语而伪造输出。级别在函数内用有限集合验证之后才拼接 SQL；这里拼的是已验证关键字，而数值参数仍应使用占位符。

## 3. 保存完整实验入口

下面是 `labs/transactions/isolation/observations.py` 完整 checkpoint。两连接共享本次新建的 schema；5 秒 statement_timeout 让实验出错时不会无限等待，它不参与安排事件顺序。输入连接必须是本入口创建的空闲 autocommit 连接；函数不会替调用者初始化或清空账户。

<!-- checkpoint: labs/transactions/isolation/observations.py -->

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def dirty_read(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "READ UNCOMMITTED"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        with writer.transaction(force_rollback=True):
            writer.execute("UPDATE accounts SET balance=70 WHERE id=1")
            own = writer.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
            other = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
        after = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
    return own, other, after


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe overlapping PostgreSQL transactions")
    parser.add_argument("--level", choices=["READ COMMITTED", "READ UNCOMMITTED"], default="READ COMMITTED")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as writer, psycopg.connect(dsn, autocommit=True, connect_timeout=5) as reader:
        schema = "t01_" + uuid4().hex
        writer.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        for conn in (writer, reader):
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.execute("SET statement_timeout = '5s'")
        try:
            writer.execute(Path(__file__).with_name("schema.sql").read_text())
            print(dirty_read(writer, reader, args.level))
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

运行并核对：

```bash
uv run python -m labs.transactions.isolation.observations --level 'READ COMMITTED'
uv run python -m labs.transactions.isolation.observations --level 'READ UNCOMMITTED'
```

两个命令都应输出 `(70, 100, 100)`。接下来创建测试文件，把这个观察变成可重复的断言。

## 4. 把两个连接的观察保存为测试

保留 v0 的转账测试。新建 `tests/transactions/isolation/test_t01_observations.py`，完整内容如下。fixture 先初始化，再把同一个 schema 的两个连接交给测试；每个参数化用例有自己的新数据。

<!-- checkpoint: tests/transactions/isolation/test_t01_observations.py -->

```python
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from labs.transactions.isolation.observations import dirty_read


@pytest.fixture
def connections():
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as writer, psycopg.connect(dsn, autocommit=True) as reader:
        schema = "t01_" + uuid4().hex
        writer.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (writer, reader):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            writer.execute(Path("labs/transactions/isolation/schema.sql").read_text())
            yield writer, reader
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.mark.parametrize("level", ["READ COMMITTED", "READ UNCOMMITTED"])
def test_v1_dirty_read(connections, level):
    writer, reader = connections
    assert dirty_read(writer, reader, level) == (70, 100, 100)
    assert reader.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(100,), (100,)]


def test_v1_invalid_level(connections):
    writer, reader = connections
    with pytest.raises(ValueError, match="unsupported isolation level"):
        dirty_read(writer, reader, "INVALID")
```

```bash
uv run python -m pytest tests/transactions/isolation/test_t01_observations.py -q
```

预期 `3 passed`。测试直接检查本版返回的三个值、回滚后的两个余额，以及非法隔离级别被拒绝。后续版本会在这个文件中追加测试，保留本节 fixture 和用例。

本版证明这个调度下没有脏读，不证明任意报表读取都一致。下一版让写事务真正提交，并把提交放在报表两条 SELECT 之间，看两个“已提交值”能否组成错误的总额。
