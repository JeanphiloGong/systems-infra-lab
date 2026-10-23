# T03 v0：复现丢失更新

两个请求各自读10、计算9、写回，最后9而非期望8。我们压缩为两连接、一行库存和四条autocommit语句，保留应用层读取后覆盖的漏洞。

## 1. 准备输入

从仓库根目录执行（仅连接本实验的临时数据库）：

```bash
uv sync --locked
docker compose -f infra/postgres.compose.yaml up -d --wait
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
```

新建 `labs/transactions/locking/schema.sql`，完整 checkpoint：

```sql
CREATE TABLE inventory (id integer PRIMARY KEY, quantity integer NOT NULL CHECK (quantity >= 0));
INSERT INTO inventory VALUES (1, 10);
```

当前只保留一行库存。版本字段将在冲突检测需要它时加入，第二资源留待死锁实验。

## 2. 组装可运行检查点

四步顺序为读10→读10→写9→写9。autocommit使每条SQL独立提交，不需线程或sleep。

以下完整替换 `labs/transactions/locking/locking.py`。main创建唯一schema，finally仅删除自己的schema；import不会连接数据库。

<!-- checkpoint: labs/transactions/locking/locking.py -->

```python
from __future__ import annotations

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


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t03_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            print(lost_update(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.locking.locking
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/transactions/locking/test_t03_locking.py -q
```

</details>

输出应为(10,10,9)。将函数中b的SELECT临时移到第一次UPDATE之后得到(10,9,8)，然后移回。这个patch只改变事件顺序，说明异常来自先读后覆盖。冻结反例，下一版增加版本条件。
