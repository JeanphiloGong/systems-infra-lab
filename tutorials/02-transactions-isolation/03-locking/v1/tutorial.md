# T03 v1：条件更新检测冲突

v0两个请求都认为完成，实际只扣一次。需要让写入验证读取后的状态是否仍有效。version条件与quantity>0一起放进UPDATE，由数据库原子判断。

## 1. 准备输入

前置[v0](../v0/tutorial.md)，保留环境。本版两个请求持有同一个旧版本，第一条条件更新递增version，第二条旧版本条件更新零行。不引入自动重试。旧schema缺乏版本信息，现在完整替换schema.sql为：

```sql
CREATE TABLE inventory (id integer PRIMARY KEY, quantity integer NOT NULL CHECK (quantity >= 0), version integer NOT NULL);
INSERT INTO inventory VALUES (1, 10, 0);
```

每次运行创建新schema，因此直接使用新初始化SQL，不对已有业务数据库迁移。

## 2. 组装可运行检查点

新增optimistic函数返回两个rowcount；parser加入--optimistic，初始化后选择该函数。SQL使用quantity=quantity-1及version条件，不能拿旧数量直接覆盖。

以下完整替换 `labs/transactions/locking/locking.py`。main创建唯一schema，finally仅删除自己的schema；import不会连接数据库。

<!-- checkpoint: labs/transactions/locking/locking.py -->

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def lost_update(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int, int]:
    a = first.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]
    b = second.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]
    first.execute("UPDATE inventory SET quantity=%s WHERE id=1", (a - 1,))
    second.execute("UPDATE inventory SET quantity=%s WHERE id=1", (b - 1,))
    return a, b, first.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]


def optimistic(conn: psycopg.Connection) -> tuple[int, int]:
    row = conn.execute("SELECT quantity,version FROM inventory WHERE id=1").fetchone()
    statement = (
        "UPDATE inventory SET quantity=quantity-1,version=version+1 "
        "WHERE id=1 AND version=%s AND quantity>0"
    )
    changed = conn.execute(statement, (row[1],)).rowcount
    conflict = conn.execute(statement, (row[1],)).rowcount
    return changed, conflict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimistic", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t03_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            print(optimistic(first) if args.optimistic else lost_update(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.locking.locking --optimistic
uv run python -m pytest tests/transactions/locking/test_t03_locking.py -q
```

--optimistic输出(1,0)，默认仍是(10,10,9)。真实测试还断言quantity=9/version=1。这个已初始化且库存充足的例子里0来自旧版本；一般情况下0还可能表示缺失记录或库存不足。初始化后临时将quantity改成0，乐观模式得到(0,0)，验证无库存不会扣减，然后删除临时更新。下一版改用行锁比较等待成本。
