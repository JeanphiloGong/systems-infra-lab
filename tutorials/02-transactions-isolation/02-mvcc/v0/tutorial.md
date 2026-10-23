# T02 v0：事务已经开始，快照就确定了吗？

值班页面打开一个事务，稍后才查询医生状态。两者之间另一连接让医生 1 下班，页面会看到旧状态还是新状态？T01 展示了 RR 重复读取不变，但我们还没有定位快照建立的时刻。

沿用 T01 的环境，`uv sync --locked` 后设置临时数据库的 `SYSTEMS_LAB_DATABASE_URL`。本模块所有 SQL 只访问新建的 t02_ schema；模型为两名医生，不实现排班系统。

## 1. 从值班记录开始

新建 `labs/transactions/mvcc/schema.sql`，完整初始化 checkpoint：

```sql
CREATE TABLE doctors (
    id integer PRIMARY KEY,
    on_call boolean NOT NULL
);
INSERT INTO doctors VALUES (1, true), (2, true);
```

这两个 true 表示初始都在岗。初始化模式与 T01 一样：唯一 schema、SET search_path、执行 SQL。没有外键或版本列，因为现在的问题是观察数据库提供的快照，不是先实现它。

## 2. 先读，再让另一个事务提交

把 T01 v1 的完整 `check_t01.py` 检查程序复制为临时 `check_t02.py`：删除 dirty_read import，把 schema 前缀改为 t02_，初始化 SQL 路径改为本版 schema.sql。将 result 调用、assert 和 print 三行替换成下面 patch，其余创建和 finally 清理原样保留：

```python
        with reader.transaction():
            reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            first = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
            with writer.transaction():
                writer.execute("UPDATE doctors SET on_call=false WHERE id=1")
            second = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
        fresh = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
        assert (first, second, fresh) == (True, True, False)
        print(first, second, fresh)
```

执行 `uv run python check_t02.py`。第二次读仍为 true，而事务外读为 false，说明写者确实提交了，读者却仍读取旧快照。这个结果要求数据库能够保留旧状态；只有覆盖写入后的当前布尔值，不足以解释观察。

## 3. 把第一次 SELECT 移到提交后

只移动 `first = ...` 到 writer 事务块退出之后、second 之前，断言改为 `(False, False, False)`，重新运行。reader 的 BEGIN 和 SET TRANSACTION 都仍在 writer 提交前，但它的首个数据查询在提交后，所以看到了 false。

此处我们建立的是明确的行为结论：本例 RR 的读取快照由首次数据查询建立，而不是 Python 连接创建或单独 BEGIN。不要把示例扩展成对所有数据库命令内部行为的断言。

## 4. 保存两种执行顺序

把刚才仅有的变化表示为 `early_read` 参数：为真就在写者之前读，为假就在之后读。返回 first、second、事务外 fresh。下面为 `labs/transactions/mvcc/snapshots.py` 完整 checkpoint；main 沿用 T01 独立 schema 生命周期，增加 `--early-read` 来选择调度。

<!-- checkpoint: labs/transactions/mvcc/snapshots.py -->

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def snapshot_timing(reader: psycopg.Connection, writer: psycopg.Connection, *, early_read: bool) -> tuple[bool, bool, bool]:
    with reader.transaction():
        reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        if early_read:
            first = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
        with writer.transaction():
            writer.execute("UPDATE doctors SET on_call=false WHERE id=1")
        if not early_read:
            first = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
        second = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
    fresh = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
    return first, second, fresh


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe snapshot establishment in PostgreSQL")
    parser.add_argument("--early-read", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as reader, psycopg.connect(dsn, autocommit=True, connect_timeout=5) as writer:
        schema = "t02_" + uuid4().hex
        reader.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (reader, writer):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            reader.execute(Path(__file__).with_name("schema.sql").read_text())
            print(snapshot_timing(reader, writer, early_read=args.early_read))
        finally:
            reader.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.mvcc.snapshots --early-read
uv run python -m labs.transactions.mvcc.snapshots
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/transactions/mvcc/test_t02_snapshots.py -q
```

</details>

输出分别为 `(True, True, False)` 和 `(False, False, False)`。删除临时 check_t02.py，保留模块入口。现在冻结这个观察；下一版用一个明确受限的版本列表模型解释为什么旧快照仍能得到旧值。
