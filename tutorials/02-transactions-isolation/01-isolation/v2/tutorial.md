# T01 v2：每次都读已提交数据，为什么总额还是错？

余额报表为了复用两个查询，先读取 A，再读取 B，最后在 Python 相加。v1 已证明未提交扣款不会泄漏，但如果转账恰好在两次读取之间提交，会发生什么？本版沿用两账户和两个连接；新增的只有一个明确的提交位置。

完成 [v1](../v1/tutorial.md)，保留 v0 的 `transfer.py` 与 `schema.sql`。总额不变量仍为 200。实验函数要求初始 100/100，CLI 每次重新初始化；不要在同一组已经转账的数据上重复调用后仍期待相同结果。

## 1. 把提交放在两次查询中间

新增下面的 checkpoint 函数到 `observations.py`，并在顶部导入 `from labs.transactions.isolation.transfer import transfer`。保留 v1 代码：

```python
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
```

检查这一步时，在 v1 main 的初始化后，把 `print(dirty_read(...))` 替换为 `print(read_skew(writer, reader, args.level))`，用 `--level 'READ COMMITTED'` 运行，得到 `(100, 130, 200)`。

事件顺序为 R 读 A=100 → W 完整转账并提交 → R 读 B=130。没有任何一条查询读到未提交值，可组合出的 230 从未是数据库的真实总额。这就是本例的 Read Skew：同一个报表混用了不同时间的已提交状态。把读取放进一个 RC 事务也不会改变“每条语句建立快照”的行为。

最后的 `sum(balance)` 只是一条 SQL，因此它在同一个语句快照里求和，结果为 200。对于这个简单报表，改成一条聚合 SQL 就够了；跨多个查询的复杂报表则需要考虑事务级快照。

## 2. 让两个查询共享快照

这是一个配置 patch：在 parser 的 choices 中增加 `REPEATABLE READ`，用相同函数运行该级别，得到 `(100, 100, 200)`。第一条 SELECT 建立事务快照；后来的转账虽然已提交，第二条 SELECT 仍读取原快照中的 B=100。不是在连接创建时，也不是仅执行 BEGIN 就冻结所有可见数据。

这里 RR 报表更旧，却在本次读取范围内一致。事务越长，旧快照保留越久，可能影响版本回收；它也不自动防止所有跨行业务约束异常，后面的 T02 会用 Write Skew 展示限制。

## 3. 保留两个实验的完整入口

当前只有被替换的 print，旧实验没法从 CLI 选择。新增 `--scenario`，允许 dirty/skew，把对应函数分支写进 main；这只是实验选择，不引入调度框架。以下为完整 `labs/transactions/isolation/observations.py` checkpoint，所有行为均来自前两版和上述两个增量。

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe overlapping PostgreSQL transactions")
    parser.add_argument("--scenario", choices=["dirty", "skew"], default="dirty")
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
            else:
                print(read_skew(writer, reader, args.level))
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.isolation.observations --scenario skew --level 'READ COMMITTED'
uv run python -m labs.transactions.isolation.observations --scenario skew --level 'REPEATABLE READ'
uv run python -m pytest tests/transactions/isolation/test_t01_observations.py -k v2 -q
```

核对两次分别为 `(100, 130, 200)`、`(100, 100, 200)`。缺失账户不是本观察函数的支持输入，它只接受本模块创建的两账户实验状态；业务输入验证仍由 transfer 负责。

冻结 v2：现在能区分脏读与读取偏斜，理解语句快照和事务快照。下一版不改变已有行，而插入一个匹配范围查询的新账户，观察结果集合是否变化。
