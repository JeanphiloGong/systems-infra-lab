# T01 v3：相同范围查询为什么多了一行？

运营页面先统计余额至少 50 的账户数，稍后重复同一查询。如果另一事务在两次查询之间创建新账户，第二次是否会多一行？v2 观察已有行的新版本，本版观察匹配谓词的集合变化。

前置 [v2](../v2/tutorial.md)。仍用相同临时数据库和初始化 SQL。本次第三个账户存入 50，所以真实总额变成 250 是输入带来的正确变化，不是转账丢钱。我们检查的是集合可见性。

## 1. 在两次范围读取之间插入

打开 `labs/transactions/isolation/observations.py`，将下面完整函数放在 `read_skew` 之后、`main` 之前。已有 imports 保留：

```python
def phantom_read(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "REPEATABLE READ"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        before = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
        with writer.transaction():
            writer.execute("INSERT INTO accounts VALUES (3, 50)")
        after = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
    fresh = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
    return before, after, fresh
```

检查这个函数时，将 v2 main 的 skew 分支临时改为 `print(phantom_read(writer, reader, args.level))`。运行 `--scenario skew --level 'READ COMMITTED'` 得到 `(2, 3, 3)`。这里临时沿用旧命令名称，只为先验证一个函数；最后一步会正式新增 phantom 选项。

两次 WHERE 完全相同，但中间有一次提交，因此 RC 的第二个语句快照包含新行。这是本例的 Phantom Read。`fresh` 的缩进有意义：它在 reader 事务块外执行，读取更新的快照。

## 2. 固定事务快照之后

保持函数不变，把命令参数改为 `REPEATABLE READ`，结果为 `(2, 2, 3)`。第二次范围查询仍看不到新行，但第三次事务外查询看到它，说明插入已经成功，并没有被这个普通读取锁住。

事务快照在第一次 SELECT 建立。若先 BEGIN，等待插入提交，再做第一次 SELECT，它就会看到第三行。PostgreSQL 的 RR 比 SQL 标准对该级别的最低要求更强，能够避免这里的幻读；不要把别的数据库对同名级别的行为直接套过来。避免这个幻读仍不等于所有执行都可串行化。

## 3. 把实验接回入口

撤销刚才临时替换的 skew 调用，在 `--scenario` 选项添加 phantom，并为它增加分支。下面是当前 `labs/transactions/isolation/observations.py` 完整 checkpoint：

<!-- checkpoint: labs/transactions/isolation/observations.py -->

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from labs.transactions.isolation.transfer import transfer


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


def read_skew(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "REPEATABLE READ"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        first = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
        transfer(writer, 1, 2, 30)
        second = reader.execute("SELECT balance FROM accounts WHERE id=2").fetchone()[0]
        single_statement = reader.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    return first, second, single_statement


def phantom_read(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "REPEATABLE READ"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        before = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
        with writer.transaction():
            writer.execute("INSERT INTO accounts VALUES (3, 50)")
        after = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
    fresh = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
    return before, after, fresh


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe overlapping PostgreSQL transactions")
    parser.add_argument("--scenario", choices=["dirty", "skew", "phantom"], default="dirty")
    parser.add_argument("--level", choices=["READ COMMITTED", "READ UNCOMMITTED", "REPEATABLE READ"], default="READ COMMITTED")
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
            if args.scenario == "dirty":
                print(dirty_read(writer, reader, args.level))
            elif args.scenario == "skew":
                print(read_skew(writer, reader, args.level))
            else:
                print(phantom_read(writer, reader, args.level))
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.isolation.observations --scenario phantom --level 'READ COMMITTED'
uv run python -m labs.transactions.isolation.observations --scenario phantom --level 'REPEATABLE READ'
```

输出分别是 `(2, 3, 3)`、`(2, 2, 3)`。这两个命令使用真实服务器和显式调用顺序，没有 sleep 或预制隔离结果。

## 4. 追加谓词查询的回归检查

在 `tests/transactions/isolation/test_t01_observations.py` 的函数导入行增加 `phantom_read`：

```python
from labs.transactions.isolation.observations import dirty_read, read_skew, phantom_read
```

保留已有用例和 fixture，在文件末尾追加：

```python
@pytest.mark.parametrize("level, expected", [
    ("READ COMMITTED", (2, 3, 3)),
    ("REPEATABLE READ", (2, 2, 3)),
])
def test_v3_phantom_read(connections, level, expected):
    writer, reader = connections
    assert phantom_read(writer, reader, level) == expected
```

```bash
uv run python -m pytest tests/transactions/isolation/test_t01_observations.py -k v3 -q
```

预期 `2 passed, 5 deselected`。RR 用例中事务内的第二次计数仍为 2，事务外已变为 3，两项必须同时成立，才能区分“固定快照”与“插入根本没有完成”。

现在冻结 v3：能观察单行可见性、跨语句混合快照和谓词集合变化。下一版把这些证据与 ACID 对齐，尤其明确我们还没有证明什么。
