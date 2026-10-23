# Q04 v0：每次现场汇总，先建立答案基准

仪表盘需要每天的销售额。先不放缓存：30,000 条明细分为 30 天，每条金额为 10，因此每一天必须返回 10,000。连续执行两次 GROUP BY，结果不变，但数据库仍要执行聚合。

## 从缺口到实现

query 是业务查询，plan 用 PostgreSQL 的 EXPLAIN ANALYZE BUFFERS 再实际执行它并保留完整 JSON。summary 只投影根节点的实际行数、耗时与 buffer hit/read。连续执行能够观察热缓存，不能假定第二次没有数据库工作。返回的 queries=2 仅指两次业务查询，后续两个 EXPLAIN ANALYZE 也会执行查询并产生额外开销。

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

将下面的完整代码保存为 `labs/query/derived/v0.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/query/derived/v0.py -->

```python
import json

from labs.query.derived.common import database, plan, summary


def run():
    with database() as (connection, _):
        query = "SELECT day,sum(amount) FROM sales GROUP BY day ORDER BY day"
        first = connection.execute(query).fetchall()
        second = connection.execute(query).fetchall()
        assert first == second == [(day, 10000) for day in range(30)]
        plans = [plan(connection, query), plan(connection, query)]
        return {"results": first, "queries": 2, "costs": [summary(p) for p in plans], "plans": plans}


if __name__ == "__main__":
    print(json.dumps(run()))
```

在仓库根目录或重建后的目录，执行实验模块；独立回放命令从仓库根目录执行：

```bash
uv run python -m labs.query.derived.v0
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/query/derived/replay_q04.py --version 0
```

</details>

## 验证与边界

检查两次结果都等于显式构造的 30 个日汇总。计划中的实际输入行数是 30,000，输出是 30。根节点 buffer 已包含子节点，不要再次相加。这个版本保证查询语句快照内的正确结果，代价是每次聚合。下一版保存结果，但必须面对刷新前的旧读。

回放将本页所有 checkpoint 文件写入新的临时目录，PYTHONPATH 仅指向该目录，再启动独立解释器执行对应版本。缺少 DSN 时明确失败，不以跳过冒充成功。数据库 buffer hit/read 是 PostgreSQL 层的访问，不直接等于物理设备 I/O；EXPLAIN 的耗时为本机采样，不能替代容量测试。逻辑 TTL 时钟与数据库锁等待的墙钟测量分别命名，避免混淆。
