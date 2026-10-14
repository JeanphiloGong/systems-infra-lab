# E04 v2：真实 postgres_fdw 连接与扫描成本

继续相同的客户/订单模型，但本版直接查询两个源。Compose 中 orders、customers、warehouse 是三个独立 PostgreSQL 进程；仓库的 postgres_fdw 分别建立服务器和用户映射，导入两组 foreign tables。使用固定镜像摘要；作者实测 PostgreSQL 16.14、postgres_fdw 1.1，脚本输出实际版本。

`FEDERATED_REPORT` 通过 customer_id 连接两个远程表。先测无谓词读取，订单和客户各返回 100 行；再执行两侧 region='west' 的真实 join。检查两个 Foreign Scan 的 Remote SQL 都含该谓词，报表仍为 C1=10、C2=20、C3=30。

`measure()` 读取 coordinator 的 EXPLAIN ANALYZE JSON：
- transferred 是每个 Foreign Scan 的 Actual Rows × Actual Loops；本查询完整耗尽输入、没有 LIMIT/本地过滤，它表示到达协调节点的数据行，不是网络字节或协议开销。
- scanned 来自在独立源连接上重执行相同 Remote SQL 的 EXPLAIN ANALYZE：Seq Scan 的 Actual Rows 加 Rows Removed by Filter，再乘 loops。它是无并发变更时的重复测量，不冒充第一次网络请求的同一条遥测。
- 本例故意没有 region 索引。选择性条件减少传输量到每源 3 行，但每个源仍顺序检查 100 行。不能把返回三行写成只扫描三行。
- execution_ms 是该次 coordinator EXPLAIN 的观测耗时，包含远程执行影响；脚本随后取结果和测远程计划还会额外执行查询，不是完整应用端延迟。

完整扫描传输 200 行；谓词下推后传输 6 行、扫描仍为 200 行。不要硬编码这些“测量值”：脚本从计划节点计算它们，再用已知数据量校验。跨源 join 在协调节点完成，FDW 并不把两个独立服务器变成同一个事务数据库。

## 环境与执行

需要 Docker Compose、Python 3.12+、仓库 uv 环境中的 psycopg。三实例只使用本机端口 55471–55473；公开密码仅限本实验。每次 experiment 重置该专用栈的 public schema，不得连接现有业务库。各版本依次运行，不能并发重置。

```bash
docker compose -f labs/dataflows/analytics/compose.yaml up -d --wait
E04_LIVE=1 uv run python -m labs.dataflows.analytics.v2
E04_LIVE=1 uv run pytest tests/dataflows/analytics/test_e04_replay.py -q
docker compose -f labs/dataflows/analytics/compose.yaml down --volumes
```

测试把本篇三个完整文件提取到空目录，再以该目录为 cwd/PYTHONPATH 启动独立 Python 子进程，使用运行中的专用栈。没有 E04_LIVE 时只检查围栏与源码相等，live 测试明确 skip。首次拉取镜像需要网络。

手动复现也可在空目录按下面标记路径创建三个文件，在那个目录启动 Compose 后使用安装了 psycopg 的 Python 执行模块。命名空间包不需要额外 __init__.py。最后清理只删除 systems-e04 容器、网络和匿名数据卷。

## 完整检查点

```text
v2.py       本版实验与断言
pg.py         共享 SQL 操作、摄取事务、报表与计划测量
compose.yaml  两个独立源进程与协调/分析实例
```

<!-- checkpoint: labs/dataflows/analytics/v2.py -->

```python
"""Measure a real postgres_fdw join across two independently queried sources."""
import json
from labs.dataflows.analytics.pg import FEDERATED_REPORT, configure_federation, connect, measure, reset


def experiment():
    reset()
    configure_federation()
    baseline = measure("SELECT id,customer_id,amount FROM remote_orders.orders")
    baseline_customers = measure("SELECT id,name FROM remote_customers.customers")
    selective = measure(FEDERATED_REPORT)
    assert selective["rows"] == [("C1", 10), ("C2", 20), ("C3", 30)]
    assert {s["source"] for s in selective["sources"]} == {"orders", "customers"}
    for sample in selective["sources"]:
        assert "WHERE" in sample["sql"] and "west" in sample["sql"]
        assert sample["scanned"] == 100 and sample["transferred"] == 3
    full = baseline["sources"] + baseline_customers["sources"]
    assert sum(s["transferred"] for s in full) == 200
    with connect("warehouse") as db:
        extension = db.execute("SELECT extversion FROM pg_extension WHERE extname='postgres_fdw'").fetchone()[0]
        server_version = db.execute("SHOW server_version").fetchone()[0]
    return dict(postgres=server_version, postgres_fdw=extension, full=full, selective=selective)


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

<!-- checkpoint: labs/dataflows/analytics/pg.py -->

```python
"""SQL operations for the dedicated, disposable E04 PostgreSQL sources."""
import os
from pathlib import Path
import subprocess

import psycopg
from psycopg import sql

PORTS = {"orders": 55471, "customers": 55472, "warehouse": 55473}
COMPOSE = Path(__file__).with_name("compose.yaml")


def connect(source):
    if os.environ.get("E04_LIVE") != "1":
        raise RuntimeError("set E04_LIVE=1 for the disposable systems-e04 stack")
    return psycopg.connect(host="127.0.0.1", port=PORTS[source], user="e04",
                          password="e04_local_only", dbname="e04",
                          connect_timeout=3, autocommit=True)


def compose(*arguments):
    subprocess.run(["docker", "compose", "-f", str(COMPOSE), *arguments],
                   check=True, capture_output=True, text=True, timeout=180)


def reset():
    """Each version starts with the same two source schemas and empty warehouse."""
    for source in PORTS:
        with connect(source) as db:
            if source == "warehouse":
                db.execute("DROP SCHEMA IF EXISTS remote_orders CASCADE; DROP SCHEMA IF EXISTS remote_customers CASCADE")
            db.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
    with connect("orders") as db:
        db.execute("CREATE TABLE orders(id int PRIMARY KEY, customer_id int, amount int, region text, business_day int, revision int)")
        db.execute("INSERT INTO orders SELECT i,i,i*10,CASE WHEN i<=3 THEN 'west' ELSE 'east' END,1,i FROM generate_series(1,100) i")
        db.execute("ANALYZE orders")
    with connect("customers") as db:
        db.execute("CREATE TABLE customers(id int PRIMARY KEY, name text, region text, revision int)")
        db.execute("INSERT INTO customers SELECT i,'C'||i,CASE WHEN i<=3 THEN 'west' ELSE 'east' END,i FROM generate_series(1,100) i")
        db.execute("ANALYZE customers")
    with connect("warehouse") as db:
        db.execute("""
            CREATE TABLE batches(source text, batch_id text, watermark int, rows_loaded int,
                                 loaded_at timestamptz DEFAULT clock_timestamp(), PRIMARY KEY(source,batch_id));
            CREATE TABLE order_fact(id int PRIMARY KEY, customer_id int, amount int, region text,
                                    business_day int, revision int, source_batch text);
            CREATE TABLE customer_dim(id int PRIMARY KEY, name text, region text, revision int, source_batch text);
        """)


def load(source, batch_id):
    """One source per transaction, paused writers; monotonically increasing revisions."""
    target = "order_fact" if source == "orders" else "customer_dim"
    columns = ["id", "customer_id", "amount", "region", "business_day", "revision"] if source == "orders" else ["id", "name", "region", "revision"]
    with connect("warehouse") as warehouse, warehouse.transaction():
        if warehouse.execute("SELECT 1 FROM batches WHERE source=%s AND batch_id=%s", (source, batch_id)).fetchone():
            return 0
        low = warehouse.execute("SELECT coalesce(max(watermark),0) FROM batches WHERE source=%s", (source,)).fetchone()[0]
        with connect(source) as db, db.transaction():
            db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            high = db.execute(sql.SQL("SELECT coalesce(max(revision),0) FROM {}").format(sql.Identifier(source))).fetchone()[0]
            rows = db.execute(sql.SQL("SELECT {} FROM {} WHERE revision>%s AND revision<=%s ORDER BY revision").format(
                sql.SQL(",").join(map(sql.Identifier, columns)), sql.Identifier(source)), (low, high)).fetchall()
        all_columns = columns + ["source_batch"]
        statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT(id) DO UPDATE SET {}").format(
            sql.Identifier(target), sql.SQL(",").join(map(sql.Identifier, all_columns)),
            sql.SQL(",").join(sql.Placeholder() for _ in all_columns),
            sql.SQL(",").join(sql.SQL("{}=EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in all_columns[1:]))
        with warehouse.cursor() as cursor:
            cursor.executemany(statement, [(*row, batch_id) for row in rows])
        warehouse.execute("INSERT INTO batches(source,batch_id,watermark,rows_loaded) VALUES (%s,%s,%s,%s)", (source, batch_id, high, len(rows)))
        return len(rows)


COPIED_REPORT = """
    SELECT c.name,sum(o.amount) FROM order_fact o
    JOIN customer_dim c ON c.id=o.customer_id
    WHERE o.region='west' AND c.region='west' GROUP BY c.name ORDER BY c.name
"""


def copied_report():
    with connect("warehouse") as db:
        return db.execute(COPIED_REPORT).fetchall()


def provenance():
    with connect("warehouse") as db:
        return db.execute("SELECT source,batch_id,watermark,rows_loaded FROM batches ORDER BY source,batch_id").fetchall()


def configure_federation():
    with connect("warehouse") as db:
        db.execute("CREATE EXTENSION postgres_fdw")
        for source in ("orders", "customers"):
            db.execute(sql.SQL("CREATE SERVER {} FOREIGN DATA WRAPPER postgres_fdw OPTIONS(host {},port '5432',dbname 'e04',connect_timeout '2',fetch_size '10')").format(sql.Identifier(source), sql.Literal(source)))
            db.execute(sql.SQL("CREATE USER MAPPING FOR CURRENT_USER SERVER {} OPTIONS(user 'e04',password 'e04_local_only')").format(sql.Identifier(source)))
            db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier("remote_" + source)))
            db.execute(sql.SQL("IMPORT FOREIGN SCHEMA public LIMIT TO ({}) FROM SERVER {} INTO {}").format(sql.Identifier(source), sql.Identifier(source), sql.Identifier("remote_" + source)))


FEDERATED_REPORT = """
    SELECT c.name,sum(o.amount) FROM remote_orders.orders o
    JOIN remote_customers.customers c ON c.id=o.customer_id
    WHERE o.region='west' AND c.region='west' GROUP BY c.name ORDER BY c.name
"""


def nodes(plan):
    yield plan
    for child in plan.get("Plans", []):
        yield from nodes(child)


def measure(query):
    """Measure exhausted FDW row streams; replay remote SQL separately for scan counts."""
    with connect("warehouse") as db:
        plan = db.execute("EXPLAIN (ANALYZE, VERBOSE, FORMAT JSON) " + query).fetchone()[0][0]
        rows = db.execute(query).fetchall()
    remote = []
    for node in nodes(plan["Plan"]):
        if node["Node Type"] != "Foreign Scan":
            continue
        source = node["Relation Name"]
        with connect(source) as db:
            remote_plan = db.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + node["Remote SQL"]).fetchone()[0][0]["Plan"]
        scans = [n for n in nodes(remote_plan) if n["Node Type"] == "Seq Scan"]
        assert len(scans) == 1, remote_plan
        scan = scans[0]
        remote.append(dict(source=source, sql=node["Remote SQL"],
                           transferred=node["Actual Rows"] * node["Actual Loops"],
                           scanned=(scan["Actual Rows"] + scan.get("Rows Removed by Filter", 0)) * scan["Actual Loops"]))
    return dict(rows=rows, sources=remote, execution_ms=plan["Execution Time"])
```

<!-- checkpoint: labs/dataflows/analytics/compose.yaml -->

```yaml
name: systems-e04
services:
  orders:
    image: postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
    environment: {POSTGRES_USER: e04, POSTGRES_PASSWORD: e04_local_only, POSTGRES_DB: e04}
    ports: ["127.0.0.1:55471:5432"]
    healthcheck:
      test: [CMD-SHELL, "pg_isready -U e04 -d e04"]
      interval: 1s
      timeout: 3s
      retries: 60
  customers:
    image: postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
    environment: {POSTGRES_USER: e04, POSTGRES_PASSWORD: e04_local_only, POSTGRES_DB: e04}
    ports: ["127.0.0.1:55472:5432"]
    healthcheck:
      test: [CMD-SHELL, "pg_isready -U e04 -d e04"]
      interval: 1s
      timeout: 3s
      retries: 60
  warehouse:
    image: postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
    environment: {POSTGRES_USER: e04, POSTGRES_PASSWORD: e04_local_only, POSTGRES_DB: e04}
    ports: ["127.0.0.1:55473:5432"]
    healthcheck:
      test: [CMD-SHELL, "pg_isready -U e04 -d e04"]
      interval: 1s
      timeout: 3s
      retries: 60
```

