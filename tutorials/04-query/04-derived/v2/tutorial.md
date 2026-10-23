# Q04 v2：普通刷新和并发刷新，对读者的影响不同

只验证刷新后的值还不够：普通刷新会持有与读操作冲突的锁。用两个真实 PostgreSQL 连接，让 reader 的事务先读 daily 并保持打开，再让 writer 普通刷新；200ms lock_timeout 使等待成为明确的 LockNotAvailable 错误，而不是测试永久挂起。

## 从缺口到实现

第一项前提实验：没有唯一索引时，REFRESH CONCURRENTLY 必须报 55000。增加仅使用列、覆盖所有行的 UNIQUE(day) 索引之后，在同一个未结束的 reader 事务下并发刷新成功。reader 使用默认 READ COMMITTED，下一条 SELECT 取得新语句快照并读到更新总额。普通刷新反向实验由 writer 在事务内刷新并保持锁，另一 reader 查询超时；writer 提交后读取恢复。最后创建 WITH NO DATA 的视图，即使有唯一索引也无法首次并发填充，捕获 0A000。

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

将下面的完整代码保存为 `labs/query/derived/v2.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/query/derived/v2.py -->

```python
import json
import os
from time import perf_counter

import psycopg
from psycopg import sql

from labs.query.derived.common import database


def run():
    with database() as (writer, schema):
        writer.execute("CREATE MATERIALIZED VIEW daily AS SELECT day,sum(amount) AS amount FROM sales GROUP BY day")
        try:
            writer.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY daily")
        except psycopg.errors.ObjectNotInPrerequisiteState as error:
            prerequisite_error = error.sqlstate
        else:
            raise AssertionError("concurrent refresh should require a unique index")
        writer.execute("CREATE UNIQUE INDEX daily_day ON daily(day)")
        writer.execute("INSERT INTO sales VALUES (30001,0,50)")
        with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as reader:
            reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            reader.execute("SET lock_timeout='200ms'")
            writer.execute("SET lock_timeout='200ms'")
            with reader.transaction():
                reader.execute("SELECT * FROM daily").fetchall()
                started = perf_counter()
                try:
                    writer.execute("REFRESH MATERIALIZED VIEW daily")
                except psycopg.errors.LockNotAvailable:
                    ordinary_wait = perf_counter() - started
                else:
                    raise AssertionError("ordinary refresh should conflict with the open reader")
                writer.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY daily")
                assert reader.execute("SELECT sum(amount) FROM daily").fetchone()[0] == 300050
            with writer.transaction():
                writer.execute("REFRESH MATERIALIZED VIEW daily")
                try:
                    reader.execute("SELECT * FROM daily")
                except psycopg.errors.LockNotAvailable:
                    read_blocked = True
                else:
                    raise AssertionError("ordinary refresh lock should block another reader")
            assert reader.execute("SELECT sum(amount) FROM daily").fetchone()[0] == 300050
        writer.execute("CREATE MATERIALIZED VIEW unpopulated AS SELECT * FROM daily WITH NO DATA")
        writer.execute("CREATE UNIQUE INDEX unpopulated_day ON unpopulated(day)")
        try:
            writer.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY unpopulated")
        except psycopg.errors.FeatureNotSupported as error:
            unpopulated_error = error.sqlstate
        else:
            raise AssertionError("concurrent refresh must not populate an unpopulated view")
        return {"missing_index_sqlstate": prerequisite_error, "unpopulated_sqlstate": unpopulated_error,
                "ordinary_wait_seconds": ordinary_wait, "ordinary_blocks_read": read_blocked,
                "concurrent_refresh_with_open_reader": True, "new_total": 300050}


if __name__ == "__main__":
    print(json.dumps(run()))
```

在仓库根目录或重建后的目录，执行实验模块；独立回放命令从仓库根目录执行：

```bash
uv run python -m labs.query.derived.v2
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/query/derived/replay_q04.py --version 2
```

</details>

## 验证与边界

两个连接的事务真实重叠，等待时间用 perf_counter 实测。失败只捕获期望 SQLSTATE，其他数据库错误会让检查失败。并发刷新并不意味着没有锁，也不支持同一个视图无限并发刷新；它需要已填充视图与合适唯一索引，并消耗额外比较/写入工作。本实验验证普通读者兼容性，不把它误写成无阻塞万能方案。

回放将本页所有 checkpoint 文件写入新的临时目录，PYTHONPATH 仅指向该目录，再启动独立解释器执行对应版本。缺少 DSN 时明确失败，不以跳过冒充成功。数据库 buffer hit/read 是 PostgreSQL 层的访问，不直接等于物理设备 I/O；EXPLAIN 的耗时为本机采样，不能替代容量测试。逻辑 TTL 时钟与数据库锁等待的墙钟测量分别命名，避免混淆。
