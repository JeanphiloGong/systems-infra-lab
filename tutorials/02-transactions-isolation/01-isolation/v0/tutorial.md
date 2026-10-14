# T01 v0：转账失败后，钱去了哪里？

账户 A 和 B 都有 100 个整数单位。用户让 A 转 30 给 B，成功后应该是 70/130；如果程序只完成扣款就失败，两边应该仍为 100/100。我们只保留两个账户和一次程序异常，不讨论支付网关、手续费或并发转账。这个模型已经足以暴露“多条 SQL 是否共同完成”的问题。

先按仓库环境文档启动临时 PostgreSQL，设置 `SYSTEMS_LAB_DATABASE_URL`，执行 `uv sync --locked`。以下命令均从仓库根目录运行。数据库必须是可丢弃的实验实例；程序会创建并清理独立 schema。金额用整数单位，避免浮点精度掩盖本课问题。

## 1. 先看两条独立提交的更新

新建 `labs/transactions/isolation/schema.sql`，这是当前完整初始化 checkpoint：

```sql
CREATE TABLE accounts (
    id integer PRIMARY KEY,
    balance integer NOT NULL CHECK (balance >= 0)
);
INSERT INTO accounts VALUES (1, 100), (2, 100);
```

以下完整临时实验直接在独立 schema 运行，不修改已有表。`autocommit=True` 让每条 UPDATE 单独提交；如果使用驱动默认事务设置，反而可能看不到本课刻意制造的错误。`%s` 是值参数占位符，不要用 f-string 拼接金额。

```python
import os
from uuid import uuid4
import psycopg
from psycopg import sql

with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
    schema = "t01_" + uuid4().hex
    conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
    try:
        conn.execute("CREATE TABLE accounts (id integer PRIMARY KEY, balance integer)")
        conn.execute("INSERT INTO accounts VALUES (1,100),(2,100)")
        conn.execute("UPDATE accounts SET balance=balance-%s WHERE id=1", (30,))
        conn.execute("UPDATE accounts SET balance=balance+%s WHERE id=2", (30,))
        print(conn.execute("SELECT balance FROM accounts ORDER BY id").fetchall())
    finally:
        conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
```

将代码放进临时 Python 文件，用 `uv run python 文件路径` 运行，得到 `[(70,), (130,)]`。目前正常路径正确，不能据此推断失败也安全。

## 2. 在扣款后停下来

对刚才脚本做一个 patch：删除第二条 UPDATE，并在第一条 UPDATE 后增加下面三行；其余代码不变。

```python
        print(conn.execute("SELECT balance FROM accounts ORDER BY id").fetchall())
        assert conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0] == 170
        raise RuntimeError("injected failure after debit")
```

重新运行会先显示 70/100，再报错并清理 schema。第一条 UPDATE 已经提交，Python 异常无法撤销这个独立提交。这里没有随机性：故障点就在扣款语句返回之后。现在缺口明确了：两次修改需要一个共同的提交边界。

## 3. 把共同提交写入函数契约

对两条更新做 patch：将它们放进 `with conn.transaction():`。连接仍为 autocommit，但这个块显式开启事务；正常退出提交，异常退出回滚。不要在块内吞掉故障后正常退出，否则可能把半笔转账提交。

我们同时把调用输入定义清楚：`transfer(conn, source, target, amount)` 接收不同的整数账户 ID 和正整数金额，返回 None 表示完成，错误通过异常返回。`bool` 在 Python 中是 int 子类，所以金额判断用 `type(amount) is int`。这不是通用银行系统，只是本课的输入契约。

扣款用 `WHERE balance >= amount`，检查 rowcount；找不到来源或余额不足就抛异常。入账也检查 rowcount，因此不存在的目标会让之前的扣款一起回滚。表的 CHECK 保证单行不为负，却不会自动保证两账户总额不变。

调用者必须提供空闲的 autocommit 连接。否则 `transaction()` 可能只是已有事务中的 savepoint，函数正常返回并不代表真正提交。因此这里明确拒绝这种输入，不隐藏提交所有权。

## 4. 运行完整检查点

下面是 `labs/transactions/isolation/transfer.py` 的完整 checkpoint。`main` 仅负责 CLI 和实验生命周期：创建唯一 schema、初始化两行、执行一次请求、打印实际余额，最后只删除自己的 schema。`finally` 不吞异常，故障运行仍返回非零退出码；连接上下文保证释放资源。

<!-- checkpoint: labs/transactions/isolation/transfer.py -->

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def transfer(
    conn: psycopg.Connection,
    source: int,
    target: int,
    amount: int,
    *,
    fail_after_debit: bool = False,
) -> None:
    """Transfer integer units; the caller supplies an idle autocommit connection."""
    if type(amount) is not int or amount <= 0:
        raise ValueError("amount must be a positive integer")
    if type(source) is not int or type(target) is not int or source == target:
        raise ValueError("source and target must be distinct integer IDs")
    if not conn.autocommit or conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
        raise ValueError("an idle autocommit connection is required")
    with conn.transaction():
        changed = conn.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id = %s AND balance >= %s",
            (amount, source, amount),
        ).rowcount
        if changed != 1:
            raise ValueError("source missing or insufficient balance")
        if fail_after_debit:
            raise RuntimeError("injected failure after debit")
        if conn.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s",
            (amount, target),
        ).rowcount != 1:
            raise ValueError("target missing")


def main() -> None:
    parser = argparse.ArgumentParser(description="Transfer in a fresh disposable schema")
    parser.add_argument("--source", type=int, default=1)
    parser.add_argument("--target", type=int, default=2)
    parser.add_argument("--amount", type=int, default=30)
    parser.add_argument("--fail-after-debit", action="store_true")
    args = parser.parse_args()
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True, connect_timeout=5) as conn:
        schema = "t01_" + uuid4().hex
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        try:
            conn.execute(Path(__file__).with_name("schema.sql").read_text())
            try:
                transfer(conn, args.source, args.target, args.amount, fail_after_debit=args.fail_after_debit)
            finally:
                print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall())
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

运行正常请求和相同故障：

```bash
uv run python -m labs.transactions.isolation.transfer --amount 30
uv run python -m labs.transactions.isolation.transfer --amount 30 --fail-after-debit
uv run python -m labs.transactions.isolation.transfer --amount 0
uv run python -m pytest tests/transactions/isolation/test_t01_transfer.py -q
```

第一条显示 `[(1, 70), (2, 130)]`。第二条显示 `[(1, 100), (2, 100)]` 并抛出故障异常。第三条也是 100/100，并以 ValueError 失败。每次命令创建新数据，不会累积上次转账。

测试还覆盖余额恰好用完、余额不足、目标缺失、同账户、负金额；不仅检查抛错，还检查数据库实际余额。故障开关只是教学入口，不应开放给真实客户。连接失败会直接抛错，不存在伪造成功结果；可以用不可连接的本地端口覆盖环境变量进行验证。

现在冻结 v0：我们验证了这笔单数据库转账的成功和异常回滚。没有验证网络断连时客户端能否知道提交结果，也没有验证机器断电后的恢复。下一版保留这个事务边界，加入第二个连接，观察未提交的扣款是否可见。
