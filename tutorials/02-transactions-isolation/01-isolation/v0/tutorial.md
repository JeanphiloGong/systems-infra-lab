# T01 v0：转账执行到一半报错，已经扣掉的钱怎么办？

账户 1 和 2 各有 100 个整数单位。我们要从账户 1 转 30 给账户 2：成功应为 70/130，失败应为 100/100。最终总额必须是 200。本篇只研究同一个 PostgreSQL 数据库中的两条 UPDATE，不涉及支付网关、并发转账或机器断电。

需要 Python 函数、异常与基础 SQL。先完成 [环境准备](../../../../docs/environment.md)，启动实验 PostgreSQL 并设置 `SYSTEMS_LAB_DATABASE_URL`。所有命令都在仓库根目录运行。第一次学习时，下文文件尚不存在；按步骤创建即可。若已经写过部分内容，先核对自己的文件，再应用当前步骤。

本篇只有一条代码主线：先创建 `schema.sql`，再用同目录的 `demo.py` 观察错误，最后把修复后的动作整理成 `transfer.py`。最后才创建测试文件。每次运行都会建立独立 schema 并在结束时删除它，因此下一次仍从 100/100 开始。

## 1. 创建两行账户数据，再正常转账

先创建文件所在目录：

```bash
mkdir -p labs/transactions/isolation
```

新建 `labs/transactions/isolation/schema.sql`，内容完整如下：

```sql
CREATE TABLE accounts (
    id integer PRIMARY KEY,
    balance integer NOT NULL CHECK (balance >= 0)
);
INSERT INTO accounts VALUES (1, 100), (2, 100);
```

`PRIMARY KEY` 让账户 ID 唯一且非空；`NOT NULL` 要求填写余额；`CHECK` 拒绝负余额。这些约束不保证两条 UPDATE 一起完成。金额使用整数单位，避免浮点精度影响本课结果。

保存 SQL 文件不会执行 SQL。接下来创建 `labs/transactions/isolation/demo.py`，由它读取并执行这份 SQL：

```python
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
    schema = "t01_" + uuid4().hex
    conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        conn.execute(Path(__file__).with_name("schema.sql").read_text())
        conn.execute("UPDATE accounts SET balance=balance-%s WHERE id=1", (30,))
        conn.execute("UPDATE accounts SET balance=balance+%s WHERE id=2", (30,))
        print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall())
    finally:
        conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
```

这里的 schema 是数据库内的命名空间：随机名字把每次运行的表隔开。`SET search_path` 让本连接的 `accounts` 指向刚建的表，`sql.Identifier` 安全地引用 schema 名称；这与 `%s` 传入普通数值是两种不同用途。`Path(__file__).with_name("schema.sql")` 找到脚本旁的 SQL 文件，所以从第一步到最后都使用同一份表定义。

连接的 `with` 负责关闭连接；`finally` 在正常或异常结束时都尝试删除本次 schema。删除实验表是清理，不等于撤销转账。`autocommit=True` 表示没有显式事务块时，每条语句独立提交；两次 UPDATE 之间已经存在一个只扣款的已提交状态。

`%s` 是值占位符，`(30,)` 是只含一个元素的元组；不要用 f-string 拼接金额。`fetchall()` 返回行元组组成的列表，每行这里是 `(id, balance)`。

运行：

```bash
uv run python labs/transactions/isolation/demo.py
```

预期 `[(1, 70), (2, 130)]`。正常转账看起来正确，下一步检查两条更新之间报错会怎样。

## 2. 在扣款成功后主动制造异常

“制造异常”是为了固定故障时刻：扣款语句已经成功返回，入账语句还没有执行。保留第二条 UPDATE，只在它前面加入三行。下面是对 `demo.py` 的精确修改；以 `+` 开头的是新增内容，复制时不保留 `+`：

```diff
         conn.execute("UPDATE accounts SET balance=balance-%s WHERE id=1", (30,))
+        print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall())
+        assert conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0] == 170
+        raise RuntimeError("injected failure after debit")
         conn.execute("UPDATE accounts SET balance=balance+%s WHERE id=2", (30,))
```

重新执行刚才的运行命令。程序先打印 `[(1, 70), (2, 100)]`，随后出现 `RuntimeError: injected failure after debit`，进程以非零状态退出。这次报错是预期结果。

`sum(balance)` 得到一行 `(170,)`，`fetchone()[0]` 取出其中的数字。`assert ... == 170` 确认我们确实复现了错误状态；它没有把 170 定义为正确业务总额。紧接着的 `raise` 让 Python 停止正常执行，因此入账 UPDATE 仍在文件里，却不会被运行。

时间顺序是：数据库扣款并提交 → Python 的 `execute()` 返回 → 我们主动抛异常。Python 异常不会自动撤销已经提交的 SQL。外层 `finally` 随后删除实验 schema，因此报错后查不到这个表；刚才打印的 70/100 是删除前的真实已提交状态。

## 3. 让两条 UPDATE 共享一个事务

我们需要保证“全做或全不做”。保留同一个故障位置，将两次更新放入 `with conn.transaction():`。异常离开这个块时 Psycopg 发出 ROLLBACK；正常离开时发出 COMMIT。

将 `demo.py` 完整替换为下面的代码。删除第 2 步用于观察中途状态的 print 和 `assert == 170`；把读取余额放在事务块外，让它发生在回滚以后：

```python
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
    schema = "t01_" + uuid4().hex
    conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        conn.execute(Path(__file__).with_name("schema.sql").read_text())
        try:
            with conn.transaction():
                conn.execute("UPDATE accounts SET balance=balance-%s WHERE id=1", (30,))
                raise RuntimeError("injected failure after debit")
                conn.execute("UPDATE accounts SET balance=balance+%s WHERE id=2", (30,))
        finally:
            print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall())
    finally:
        conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
```

再次运行，预期先显示 `[(1, 100), (2, 100)]`，随后仍报同样的 `RuntimeError`。内层 `finally` 执行时事务已经回滚；外层 `finally` 最后删除 schema。读取结果不同来自事务边界，不能归因于清理。

再删除代码中唯一的 `raise RuntimeError(...)` 行，重新运行。预期成功输出 `[(1, 70), (2, 130)]`。两次实验的区别只有是否在扣款后抛异常；两条 UPDATE 现在属于同一个事务。

## 4. 把同一个动作保存成可重复调用的函数

目前每次切换成功与失败都要手改脚本。下一步把两条更新提取成 `transfer(conn, source, target, amount)`，由 `--fail-after-debit` 参数控制同一个故障位置。CLI、参数检查和实验清理分别有自己的职责：

- `transfer` 接受不同的整数账户 ID 和正整数金额；成功返回 `None`，失败抛异常。Python 的 bool 是 int 子类，故金额使用 `type(amount) is int`。
- 扣款条件 `balance >= amount` 防止余额不足；`rowcount` 检查恰好更新一行。找不到目标时抛异常，让已执行的扣款也回滚。
- 调用者提供空闲 autocommit 连接，让 `transaction()` 负责真正的顶层提交。已有事务中的嵌套块可能只创建 savepoint，不能把这种返回误认为已提交。
- `main` 解析命令行并建立、打印、清理实验数据；不吞异常。故障参数只供实验使用。

新建 `labs/transactions/isolation/transfer.py`，内容完整如下。它继续读取你在第 1 步创建的 `schema.sql`，不依赖 `demo.py`：

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

下面三条命令分别执行，每次都从新数据开始：

```bash
uv run python -m labs.transactions.isolation.transfer --amount 30
uv run python -m labs.transactions.isolation.transfer --amount 30 --fail-after-debit
uv run python -m labs.transactions.isolation.transfer --amount 0
```

第一条成功，余额为 `[(1, 70), (2, 130)]`。第二条以 RuntimeError 失败，余额为 `[(1, 100), (2, 100)]`。第三条以 ValueError 失败，余额也为 100/100。后两条的非零退出码是本次检查预期的一部分。

## 5. 创建本版测试，保存成功和失败的预期

手工对照输出容易漏掉“报错但余额已改变”。现在创建测试，直接断言数据库里的余额。测试自己的 fixture 为每个用例建立独立 schema，使用与你相同的 `schema.sql`，用完后清理；无需从 reference 分支复制文件。

```bash
mkdir -p tests/transactions/isolation
```

新建 `tests/transactions/isolation/test_t01_transfer.py`：

<!-- checkpoint: tests/transactions/isolation/test_t01_transfer.py -->

```python
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from labs.transactions.isolation.transfer import transfer


@pytest.fixture
def conn():
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as db:
        schema = "t01_" + uuid4().hex
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            db.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            db.execute(Path("labs/transactions/isolation/schema.sql").read_text())
            yield db
        finally:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.mark.parametrize("amount, expected", [(30, [(70,), (130,)]), (100, [(0,), (200,)])])
def test_transfer(conn, amount, expected):
    transfer(conn, 1, 2, amount)
    assert conn.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == expected


@pytest.mark.parametrize("source, target, amount", [
    (1, 2, 0), (1, 2, -1), (1, 2, True), (1, 2, 101),
    (9, 2, 30), (1, 9, 30), (1, 1, 30),
])
def test_invalid_request_leaves_balances_unchanged(conn, source, target, amount):
    with pytest.raises(ValueError):
        transfer(conn, source, target, amount)
    assert conn.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(100,), (100,)]


def test_failure_after_debit_rolls_back(conn):
    with pytest.raises(RuntimeError, match="injected failure"):
        transfer(conn, 1, 2, 30, fail_after_debit=True)
    assert conn.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(100,), (100,)]
```

`pytest.raises` 要求异常确实发生；随后读取余额，确认没有留下半笔转账。参数化用例分别检查普通转账、余额恰好用完、非法金额、余额不足、来源缺失、目标缺失和同账户。无效目标尤其重要：它在扣款之后才被发现，应让扣款一起回滚。

运行你刚创建的测试：

```bash
uv run python -m pytest tests/transactions/isolation/test_t01_transfer.py -q
```

预期 `10 passed`。如果文件不存在，先核对本节创建步骤；如果连接失败，先检查环境文档中的服务与连接地址。

本版最后保留 `schema.sql`、`transfer.py` 和测试文件。`demo.py` 只是前 3 步使用的实验草稿，不会被后续模块导入，可删除它。现在验证的是单数据库内正常提交和程序异常回滚；没有验证网络断连后的提交结果确认，也没有证明断电持久性。下一版加入另一个连接，观察尚未提交的扣款是否能被别人看到。
