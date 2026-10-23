# Q04 v1：物化视图能省查询工作，却不会自动变新

将每日汇总保存为 MATERIALIZED VIEW daily。创建完成后写入一笔金额为 50 的销售记录。源表总额变为 300,050，daily 仍是 300,000：写源表并不会自动刷新物化视图。

## 从缺口到实现

先明确比较的是源表现场聚合与直接读取派生行，分别记录真实执行计划。随后显式 REFRESH MATERIALIZED VIEW，检查总额才变成 300,050。查询成本下降来自少读明细，不代表维护免费；本检查点不把刷新成本隐藏为自动增量维护，也不声称刷新一定更便宜。

## 本版完整检查点

以下文件全部列出，可在空目录重建。数据源是仓库的独立 PostgreSQL 16 服务；每次运行创建随机 q04_ schema，finally 删除自己的对象。只有数据库依赖 psycopg，没有从工作树偷取隐藏实现。先在仓库根目录准备环境：

```bash
docker compose -f infra/postgres.compose.yaml up -d
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv sync --locked
```

common.py 负责隔离数据和清理；实验入口使用其提供的真实连接。

将下面的完整代码保存为 `labs/query/derived/common.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/query/derived/common.py -->

```python
import os
from contextlib import contextmanager
from uuid import uuid4

import psycopg
from psycopg import sql


@contextmanager
def database():
    schema = "q04_" + uuid4().hex
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            connection.execute("SET statement_timeout='10s'")
            connection.execute("CREATE TABLE sales (id int PRIMARY KEY, day int NOT NULL, amount int NOT NULL)")
            connection.execute("INSERT INTO sales SELECT i,i%30,10 FROM generate_series(1,30000) i")
            connection.execute("ANALYZE sales")
            yield connection, schema
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def total(connection):
    return connection.execute("SELECT sum(amount) FROM sales").fetchone()[0]


def plan(connection, query):
    return connection.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query).fetchone()[0][0]


def summary(document):
    node = document["Plan"]
    return {"rows": node["Actual Rows"], "elapsed_ms": document["Execution Time"],
            "shared_hits": node.get("Shared Hit Blocks", 0), "shared_reads": node.get("Shared Read Blocks", 0)}
```

将下面的完整代码保存为 `labs/query/derived/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/query/derived/v1.py -->

```python
import json

from labs.query.derived.common import database, plan, summary, total


def run():
    with database() as (c, _):
        c.execute("CREATE MATERIALIZED VIEW daily AS SELECT day,sum(amount) AS amount FROM sales GROUP BY day")
        before = int(c.execute("SELECT sum(amount) FROM daily").fetchone()[0])
        c.execute("INSERT INTO sales VALUES (30001,0,50)")
        stale = int(c.execute("SELECT sum(amount) FROM daily").fetchone()[0])
        fresh = total(c)
        assert before == stale == 300000 and fresh == 300050
        source = plan(c, "SELECT day,sum(amount) FROM sales GROUP BY day")
        derived = plan(c, "SELECT day,amount FROM daily")
        c.execute("REFRESH MATERIALIZED VIEW daily")
        assert c.execute("SELECT sum(amount) FROM daily").fetchone()[0] == fresh
        return {"before": before, "stale": stale, "source": fresh, "after_refresh": fresh,
                "costs": {"source": summary(source), "view": summary(derived)}, "plans": [source, derived]}


if __name__ == "__main__":
    print(json.dumps(run()))
```

在仓库根目录或重建后的目录，执行实验模块；独立回放命令从仓库根目录执行：

```bash
uv run python -m labs.query.derived.v1
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/query/derived/replay_q04.py --version 1
```

</details>

## 验证与边界

断言刷新前源与视图不同，刷新后相等。旧值是受刷新策略约束的快照，不能标为实时值。当前例子没有源写入并发刷新；一般刷新得到的是刷新所用查询快照，不保证包含其后提交的所有写入。下一版研究刷新与读者竞争同一个视图时的锁。

回放将本页所有 checkpoint 文件写入新的临时目录，PYTHONPATH 仅指向该目录，再启动独立解释器执行对应版本。缺少 DSN 时明确失败，不以跳过冒充成功。数据库 buffer hit/read 是 PostgreSQL 层的访问，不直接等于物理设备 I/O；EXPLAIN 的耗时为本机采样，不能替代容量测试。逻辑 TTL 时钟与数据库锁等待的墙钟测量分别命名，避免混淆。
