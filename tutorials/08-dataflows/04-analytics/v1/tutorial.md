# E04 v1：重复批次与迟到修正

沿用 v0 的两个独立来源、两张仓库表和来源限定的批次键。先装载两个 b1，再实际调用第二次装载：返回 0、provenance 不变，证明批次重跑没有重复计数。

接着把历史订单 1 的金额从 10 改为 35，并把客户从 1 改为 2；business_day 仍为 1，更新 revision 为 101。客户源独立把客户 2 更名为 C2-corrected，revision 也为 101。两个源分别装载 b2，必须各导入一条。新的报表是 C2-corrected=55、C3=30；旧客户 C1 不应残留金额。

读取使用 `revision > low AND revision <= high`，低水位来自该来源已提交批次。目标记录按业务主键 upsert，历史金额被覆盖，报表直接连接当前维表并重新聚合。这里明确采用当前客户名称重述历史，不维护 slowly changing dimension，也不把旧金额继续累加。

再次实际重跑两个 b2，检查报表、四条已持久化批次和事实表行数不变；订单 1 的 business_day=1、revision=101、source_batch=b2。两条 b2 水位必须分别属于 orders 和 customers。

这个 revision 协议要求源发布单调递增、不会在水位后补提交更小 revision 的变更。生产系统可改用有完整提交顺序的 CDC 游标。不要拿事件发生日期代替更新游标。本例不支持物理删除，需要 tombstone 才能扩展到该场景。

## 环境与执行

需要 Docker Compose、Python 3.12+、仓库 uv 环境中的 psycopg。三实例只使用本机端口 55471–55473；公开密码仅限本实验。每次 experiment 重置该专用栈的 public schema，不得连接现有业务库。各版本依次运行，不能并发重置。

```bash
docker compose -f labs/dataflows/analytics/compose.yaml up -d --wait
E04_LIVE=1 uv run python -m labs.dataflows.analytics.v1
E04_LIVE=1 uv run pytest tests/dataflows/analytics/test_e04_replay.py -q
docker compose -f labs/dataflows/analytics/compose.yaml down --volumes
```

测试把本篇三个完整文件提取到空目录，再以该目录为 cwd/PYTHONPATH 启动独立 Python 子进程，使用运行中的专用栈。没有 E04_LIVE 时只检查围栏与源码相等，live 测试明确 skip。首次拉取镜像需要网络。

手动复现也可在空目录按下面标记路径创建三个文件，在那个目录启动 Compose 后使用安装了 psycopg 的 Python 执行模块。命名空间包不需要额外 __init__.py。最后清理只删除 systems-e04 容器、网络和匿名数据卷。

## 完整检查点

```text
v1.py       本版实验与断言
pg.py         共享 SQL 操作、摄取事务、报表与计划测量
compose.yaml  两个独立源进程与协调/分析实例
```

<!-- checkpoint: labs/dataflows/analytics/v1.py -->

```python
"""Repeat source-scoped batches; apply late order and customer corrections."""
import json
from labs.dataflows.analytics.pg import connect, copied_report, load, provenance, reset


def experiment():
    reset()
    load("orders", "b1")
    load("customers", "b1")
    before = provenance()
    assert load("orders", "b1") == load("customers", "b1") == 0
    assert provenance() == before
    initial = copied_report()
    with connect("orders") as db:
        db.execute("UPDATE orders SET amount=35,customer_id=2,revision=101 WHERE id=1")
    with connect("customers") as db:
        db.execute("UPDATE customers SET name='C2-corrected',revision=101 WHERE id=2")
    assert load("orders", "b2") == load("customers", "b2") == 1
    corrected = copied_report()
    assert corrected == [("C2-corrected", 55), ("C3", 30)]
    batches = provenance()
    assert batches == [("customers", "b1", 100, 100), ("customers", "b2", 101, 1),
                       ("orders", "b1", 100, 100), ("orders", "b2", 101, 1)]
    assert load("orders", "b2") == load("customers", "b2") == 0
    assert provenance() == batches and copied_report() == corrected
    with connect("warehouse") as db:
        assert db.execute("SELECT business_day,revision,source_batch FROM order_fact WHERE id=1").fetchone() == (1, 101, "b2")
        assert db.execute("SELECT source_batch FROM customer_dim WHERE id=2").fetchone() == ("b2",)
        assert db.execute("SELECT count(*) FROM order_fact").fetchone()[0] == 100
    return dict(initial=initial, corrected=corrected, replayed=copied_report(), batches=batches)


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

