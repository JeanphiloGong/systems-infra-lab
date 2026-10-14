# T02 v3：把共同规则变成共同冲突点

[v2](../v2/tutorial.md) 中两个医生各写自己一行，所以 RR 没有检测到写写冲突。现在保持相同隔离级别，要求所有修改本排班组的人先更新同一条 guard 记录。这样旧快照继续执行时，冲突就落到数据库能检测的一行上。

这个策略只保护遵守协议的写者。绕过 guard 的直接 UPDATE 仍能破坏规则。模型只有一个排班组；生产系统可以按组拆分 guard，但本课不引入租约、分布式锁或自动重试框架。

## 1. 加入一条共同更新的记录

新建 `labs/transactions/mvcc/guard.sql`，完整 checkpoint：

```sql
CREATE TABLE roster_guard (id integer PRIMARY KEY, version integer NOT NULL);
INSERT INTO roster_guard VALUES (1, 0);
```

在 v2 临时检查程序初始化 doctors 的 `writer.execute(Path(...schema.sql...).read_text())` 后添加这一行（该程序已经导入 Path）：

```python
        writer.execute(Path("labs/transactions/mvcc/guard.sql").read_text())
```

这里 version 的数值本身不决定谁能下班；真正需要的是每个参与者都执行 UPDATE，形成行版本变化。只读取 guard 不产生共同写冲突。

## 2. 让过期快照撞上这个更新

将 v2 从 `with reader.transaction()` 开始到最后 `assert ... == 0` 为止的整个实验区域替换为下面 checkpoint，删除旧的所有实验断言，保留初始化（包括刚加入的 guard）和 finally 清理。连接仍为 reader/writer。它先让 writer 建立旧快照，再让 reader 完成 guard 更新和下班，最后由 writer 尝试更新 guard：

```python
        conflicted = False
        try:
            with writer.transaction():
                writer.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                writer.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()
                with reader.transaction():
                    reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                    reader.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
                    if reader.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] > 1:
                        reader.execute("UPDATE doctors SET on_call=false WHERE id=1")
                writer.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
        except psycopg.errors.SerializationFailure:
            conflicted = True
        assert conflicted
```

运行后断言成立。数据库返回 SQLSTATE 40001：writer 的 RR 快照已经过期，不能更新另一个事务后来提交的 guard 版本。我们故意让首个写者先提交，所以不用线程等待锁；失败原因来自旧快照更新，而不是 statement_timeout。

此刻一名医生已经离开，另一请求失败。直接重放它之前“看到两人”的决定仍然危险，需要在新事务里重新读取业务条件。

## 3. 重做整个请求的判断

在异常处理后追加这个 patch：

```python
        with writer.transaction():
            writer.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            writer.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
            allowed = writer.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] > 1
            if allowed:
                writer.execute("UPDATE doctors SET on_call=false WHERE id=2")
        assert allowed is False
        assert reader.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] == 1
```

重新运行完整临时程序，结果留下医生2。事务块必须已经退出并回滚，再开始重试；不能在已失败事务里继续 SQL。新事务先更新 guard，再读取条件，看到人数1，所以拒绝下班。实验只安排一次冲突，因此只做一次完整重试；真实请求需要明确次数、退避和错误传播策略，不能无界重试。

## 4. 保存完整保护实验

新建 `labs/transactions/mvcc/protected.py`，以下完整 checkpoint 返回冲突次数、重试后是否允许下班、最终人数。若旧快照更新意外没报错，显式 AssertionError 让实验失败，避免偷偷把错误行为当成功。

<!-- checkpoint: labs/transactions/mvcc/protected.py -->

```python
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def protected_schedule(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, bool, int]:
    conflicts = 0
    try:
        with second.transaction():
            second.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            second.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()
            with first.transaction():
                first.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                first.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
                if first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] > 1:
                    first.execute("UPDATE doctors SET on_call=false WHERE id=1")
            second.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
            raise AssertionError("expected a stale-snapshot write conflict")
    except psycopg.errors.SerializationFailure:
        conflicts += 1
    with second.transaction():
        second.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        second.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
        allowed = second.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] > 1
        if allowed:
            second.execute("UPDATE doctors SET on_call=false WHERE id=2")
    remaining = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
    return conflicts, allowed, remaining


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
            first.execute(Path(__file__).with_name("guard.sql").read_text())
            print(protected_schedule(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.mvcc.protected
uv run python -m pytest tests/transactions/mvcc/test_t02_protected.py -q
```

输出 `(1, False, 1)`，测试确认最终医生1为 false，医生2为 true。与 v2 的 `(2, 2, 0)` 相比，共同 guard 把原来分散的业务依赖变成了写冲突，但也让同一排班组上的修改互相争用。

另一条路线是 SERIALIZABLE 并处理数据库检测到的序列化失败，T04 会展开；本版没有实现那条路线。T02 在这里冻结：MVCC 支持旧快照，快照隔离本身不能守住任意跨行规则，保护方案必须说明共同冲突点与完整重试责任。
