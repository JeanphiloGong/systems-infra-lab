# T02 v2：两个正确快照，零个值班医生

医院要求至少一名医生在岗。两人初始都在岗，各自点击下班；程序先查询人数，大于 1 才允许自己离开。单独看每次请求似乎正确，但是两个请求可以使用不同事务同时判断。

本版回到 [v0](../v0/tutorial.md) 的真实 PostgreSQL；[v1](../v1/tutorial.md) 的列表模型只解释历史读取，不负责证明并发异常。两行分别为医生1和2，规则是跨行的 `count(on_call) >= 1`。

## 1. 先验证顺序请求

复用 v0 临时检查程序的初始化与清理，将其事务实验替换为以下 checkpoint 片段。它在初始化后的 reader/writer 连接上运行：

```python
        for conn, doctor in ((reader, 1), (writer, 2)):
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                count = conn.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
                if count > 1:
                    conn.execute("UPDATE doctors SET on_call=false WHERE id=%s", (doctor,))
        assert reader.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] == 1
```

执行临时程序不应报错。医生1提交后，医生2的新快照看到只有自己，于是留下。当前规则在这个串行调度中成立。

## 2. 让两次判断都发生在提交之前

将上面从 `for conn, doctor` 开始到末尾 `assert ... == 1` 为止的整个实验区域替换为下面 patch，包含删除旧的最终断言；只保留外层初始化和 finally 清理：

```python
        with reader.transaction():
            reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            with writer.transaction():
                writer.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                a = reader.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
                b = writer.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
                assert (a, b) == (2, 2)
                if a > 1:
                    reader.execute("UPDATE doctors SET on_call=false WHERE id=1")
                if b > 1:
                    writer.execute("UPDATE doctors SET on_call=false WHERE id=2")
        assert reader.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] == 0
```

运行后断言成立，说明规则被破坏了。嵌套的是 Python 上下文，不是同一数据库连接的子事务：writer 的块退出先提交，然后 reader 提交。两者更新不同的行，没有同一行更新冲突；每次读取也符合自己的 RR 快照。

这叫 Write Skew：事务的读取条件涉及共同规则，写入却分散到不同记录。它不同于 T01 的 Read Skew；这里坏的是提交后的业务状态，而不只是报表拼接。

## 3. 冻结这个反例

新建 `labs/transactions/mvcc/write_skew.py`。完整 checkpoint 将两次判定与结果返回，连接和 schema 生命周期仍与 v0 相同。函数假设两位医生初始在岗，不提供生产业务入口。

<!-- checkpoint: labs/transactions/mvcc/write_skew.py -->

```python
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def write_skew(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int, int]:
    with first.transaction():
        first.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        with second.transaction():
            second.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            first_count = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
            second_count = second.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
            if first_count > 1:
                first.execute("UPDATE doctors SET on_call=false WHERE id=1")
            if second_count > 1:
                second.execute("UPDATE doctors SET on_call=false WHERE id=2")
    remaining = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
    return first_count, second_count, remaining


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as first, psycopg.connect(dsn, autocommit=True, connect_timeout=5) as second:
        schema = "t02_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            print(write_skew(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.mvcc.write_skew
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/transactions/mvcc/test_t02_write_skew.py -q
```

</details>

预期 `(2, 2, 0)`，测试还直接读取两行都为 false。只检查函数返回是不够的，数据库最终内容才是违反约束的证据。

如果两个请求串行，无论谁先走，最后都应该留一人；这里得到零人，因此不能等价为这两请求的某个串行顺序。下一版仍使用 RR，增加一个明确的共享冲突点，并重新执行失败事务的整个判断。
