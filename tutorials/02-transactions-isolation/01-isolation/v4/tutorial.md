# T01 v4：我们究竟验证了 ACID 的哪一部分？

评审转账代码时，有人说“用了数据库事务，所以业务已经满足 ACID”。完成 [v0](../v0/tutorial.md) 到 [v3](../v3/tutorial.md) 后，你已经有足够的反例追问这句话。这里不再增加隔离级别，而是把观察结果对应到可以支持的结论。

## 1. 从事件轨迹出发

v0 的扣款后失败留下 100/100，而两条独立提交留下 70/100。这支持本例的 Atomicity：明确事务边界中的两次更新共同成功或回滚。它没有解决外部邮件和数据库如何共同提交。

v1 的写者读 70、读者读 100，说明 PostgreSQL 不暴露这个未提交更新；v2 RC 的 100+130，以及 v3 RC 的 2→3，说明 Isolation 不是一句“事务互不影响”。隔离级别决定允许哪些观察，本课的 RR 快照也不能被称作串行化。

先重跑以下已有检查，冻结事实而不是记缩写：

```bash
uv run python -m pytest tests/transactions/isolation/test_t01_transfer.py -q
uv run python -m pytest tests/transactions/isolation/test_t01_observations.py -q
```

下一缺口是 Consistency：数据库到底知道哪些业务规则？

## 2. 数据库约束不等于所有业务规则

表有 `CHECK (balance >= 0)`，所以写 -1 应该失败。但“从 A 减一，不给 B 加一”并不违反这个 CHECK；数据库不知道你原本想转账。

新建 `labs/transactions/isolation/acid.py`，先保存这个函数 checkpoint：

```python
import psycopg


def constraint_trace(conn: psycopg.Connection) -> tuple[int, int]:
    try:
        with conn.transaction():
            conn.execute("UPDATE accounts SET balance=-1 WHERE id=1")
    except psycopg.errors.CheckViolation:
        pass
    after_rejection = conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    with conn.transaction():
        conn.execute("UPDATE accounts SET balance=balance-1 WHERE id=1")
    after_legal_sql = conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    return after_rejection, after_legal_sql
```

检查时从 [v1 第 1 节](../v1/tutorial.md) 的完整代码块重新创建临时 `check_t01.py`：把 import 改为 `from labs.transactions.isolation.acid import constraint_trace`，把调用改为 `result = constraint_trace(writer)`，断言改为 `assert result == (200, 199)`。其余创建、初始化、清理保持不变，执行 `uv run python check_t01.py`。

异常在事务块外捕获，所以查询可以继续。第一项为 200，证明负余额操作没有生效；第二项为 199，证明合法 SQL 仍可破坏未编码的业务规则。这里刻意执行错误业务动作，不要把它接到转账接口。ACID 的 C 需要应用逻辑与数据库约束共同维护选定的不变量。

## 3. 提交后换连接，再明确持久性的边界

下一步在初始化入口中先运行约束实验，再将两余额重置为 100。调用 v0 transfer，退出写连接上下文，然后建立一个全新连接读余额，应该仍为 70/130。这样可以排除只看到了写连接自己的未提交状态。

这次检查没有重启 PostgreSQL，更没有切断机器电源。Durability 的实际保证还依赖 WAL 刷盘、synchronous_commit/fsync 配置、文件系统与存储设备。本课不从“重新连接可见”推出“断电必不丢失”；S03 与 A01 才会进一步研究恢复边界。

下面是 `labs/transactions/isolation/acid.py` 完整 checkpoint。除了刚才的函数，只加入已经解释的重置、转账、关闭和重连，以及各版本一直使用的独立 schema 生命周期。

<!-- checkpoint: labs/transactions/isolation/acid.py -->

```python
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from labs.transactions.isolation.transfer import transfer


def constraint_trace(conn: psycopg.Connection) -> tuple[int, int]:
    try:
        with conn.transaction():
            conn.execute("UPDATE accounts SET balance=-1 WHERE id=1")
    except psycopg.errors.CheckViolation:
        pass
    after_rejection = conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    with conn.transaction():
        conn.execute("UPDATE accounts SET balance=balance-1 WHERE id=1")
    after_legal_sql = conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    return after_rejection, after_legal_sql


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    schema = "t01_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            admin.execute(Path(__file__).with_name("schema.sql").read_text())
            print("constraint, business total:", constraint_trace(admin))
            admin.execute("UPDATE accounts SET balance=100")
            with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as writer:
                writer.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                transfer(writer, 1, 2, 30)
            with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as reader:
                reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                print("after reconnect:", reader.execute("SELECT balance FROM accounts ORDER BY id").fetchall())
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.isolation.acid
```

第一条输出：

```text
constraint, business total: (200, 199)
after reconnect: [(70,), (130,)]
```

## 4. 保存约束检查，再跑完整的 T01 测试

在已有的 `tests/transactions/isolation/test_t01_observations.py` 顶部增加导入：

```python
from labs.transactions.isolation.acid import constraint_trace
```

在文件末尾追加下面的测试，它使用 v1 已创建的 `connections` fixture，不需要新的辅助文件：

```python
def test_v4_constraint_and_business_rule(connections):
    writer, reader = connections
    assert constraint_trace(writer) == (200, 199)
    assert reader.execute("SELECT sum(balance) FROM accounts").fetchone()[0] == 199
```

```bash
uv run python -m pytest tests/transactions/isolation -q
```

按 v0-v4 的创建与追加步骤完成后，预期 `18 passed`：转账测试 10 项、隔离观察测试 7 项、约束测试 1 项。完整测试只覆盖你在本模块实际创建的文件，不需要 reference 分支中的旧测试。

这份证据地图就是 T01 的最终检查点：A 有故障回滚，C 有已编码约束与未编码规则的对照，I 有三个确定性调度，D 只有提交后的重连观察和明确的待验证范围。没有完成的实验不能写成结论。

继续 T02 时，会保留真实双连接调度，研究 MVCC 与 Snapshot Isolation，并构造“各自更新不同行却破坏共同规则”的 Write Skew。不要把这件事与本模块的 Read Skew 混为一谈。
