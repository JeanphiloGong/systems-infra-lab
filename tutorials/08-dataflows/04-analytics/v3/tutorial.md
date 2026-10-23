# E04 v3：两源不同步、真实停机与仓库追平

从 v0 的仓库快照和 v2 的 FDW 查询同时开始。两个 b1 的截止 revision 均为 100。一次业务变化需要两个独立提交：订单 1 先改为引用尚不存在的客户 101；客户源随后才插入该客户。

在两个提交之间执行联邦报表，它只剩 C2=20、C3=30。额外执行 LEFT JOIN 找出订单 1 的缺失客户，证明这是跨源不同步导致的漏计，而不是不同时间的两个合法合计。仓库此时仍返回旧而完整的 C1、C2、C3 报表。客户提交后联邦报表恢复为 C1new=10、C2=20、C3=30。

接着真正执行 `docker compose stop customers`。FDW server/user mapping/foreign table 配置保持原样；新连接上的联邦查询应失败，记录 SQLSTATE。仓库依然可读。finally 重新启动 customers 并等待健康检查，再验证无需重配 FDW 就能读取恢复后的源。

最后分别装载两个 b2。仓库报表必须等于已追平的联邦报表，且 provenance 显示每源从 100 变为 101、各新增装载一行。仅声明“复制数据可用”不足以通过，必须观察停机时实际查询成功。

成本比较来自同一个客户销售报表：联邦记录每源扫描和传输行数及 EXPLAIN 耗时；仓库计划记录本地扫描量和耗时，并断言不存在 Foreign Scan（每次读不访问源）。复制成本则由 batches.rows_loaded 表示，初始 200 行、修正各一行。本例不测网络字节、磁盘占用或生产吞吐。

快照可用不表示新鲜，联邦实时读取也不表示跨源一致：两个源的 revision 是局部坐标；即使一个 SQL 涉及两源，postgres_fdw 也没有提供业务上的全局提交点。单次耗时不能推导 SLA。

## 环境与执行

需要 Docker Compose、Python 3.12+、仓库 uv 环境中的 psycopg。三实例只使用本机端口 55471–55473；公开密码仅限本实验。每次 experiment 重置该专用栈的 public schema，不得连接现有业务库。各版本依次运行，不能并发重置。

```bash
docker compose -f labs/dataflows/analytics/compose.yaml up -d --wait
E04_LIVE=1 uv run python -m labs.dataflows.analytics.v3
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
E04_LIVE=1 uv run pytest tests/dataflows/analytics/test_e04_replay.py -q
```

</details>

```bash
docker compose -f labs/dataflows/analytics/compose.yaml down --volumes
```

测试把本篇三个完整文件提取到空目录，再以该目录为 cwd/PYTHONPATH 启动独立 Python 子进程，使用运行中的专用栈。没有 E04_LIVE 时只检查围栏与源码相等，live 测试明确 skip。首次拉取镜像需要网络。

手动复现也可在空目录按下面标记路径创建三个文件，在那个目录启动 Compose 后使用安装了 psycopg 的 Python 执行模块。命名空间包不需要额外 __init__.py。最后清理只删除 systems-e04 容器、网络和匿名数据卷。

## 完整检查点

```text
v3.py       本版实验与断言
pg.py         共享 SQL 操作、摄取事务、报表与计划测量
compose.yaml  两个独立源进程与协调/分析实例
```

将下面的完整代码保存为 `labs/dataflows/analytics/v3.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/dataflows/analytics/v3.py -->

```python
"""Observe a cross-source mismatch, catch-up, and real source process outage."""
import json
import psycopg
from labs.dataflows.analytics.pg import (
    COPIED_REPORT, FEDERATED_REPORT, compose, configure_federation, connect,
    copied_report, load, measure, nodes, provenance, reset,
)


def experiment():
    reset()
    configure_federation()
    load("orders", "b1")
    load("customers", "b1")
    initial = copied_report()
    # Business change spans independent commits: an order references a new customer.
    with connect("orders") as db:
        db.execute("UPDATE orders SET customer_id=101,revision=101 WHERE id=1")
    mismatch = measure(FEDERATED_REPORT)
    assert mismatch["rows"] == [("C2", 20), ("C3", 30)]
    with connect("warehouse") as db:
        orphan = db.execute("SELECT o.id FROM remote_orders.orders o LEFT JOIN remote_customers.customers c ON c.id=o.customer_id WHERE c.id IS NULL").fetchall()
    assert orphan == [(1,)]
    with connect("customers") as db:
        db.execute("INSERT INTO customers VALUES (101,'C1new','west',101)")
    converged = measure(FEDERATED_REPORT)
    assert converged["rows"] == [("C1new", 10), ("C2", 20), ("C3", 30)]
    assert copied_report() == initial
    stale_cutoffs = provenance()
    with connect("warehouse") as db:
        servers_before = db.execute("SELECT srvname,srvoptions FROM pg_foreign_server ORDER BY srvname").fetchall()
        local_plan = db.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + COPIED_REPORT).fetchone()[0][0]
    local_nodes = list(nodes(local_plan["Plan"]))
    assert not any(n["Node Type"] == "Foreign Scan" for n in local_nodes)
    local_scanned = sum((n["Actual Rows"] + n.get("Rows Removed by Filter", 0)) * n["Actual Loops"]
                        for n in local_nodes if n["Node Type"] == "Seq Scan")
    stopped = False
    try:
        compose("stop", "customers")
        stopped = True
        try:
            measure(FEDERATED_REPORT)
        except psycopg.Error as error:
            outage_sqlstate = error.sqlstate
        else:
            raise AssertionError("federation succeeded with stopped source")
        assert copied_report() == initial
        with connect("warehouse") as db:
            assert db.execute("SELECT srvname,srvoptions FROM pg_foreign_server ORDER BY srvname").fetchall() == servers_before
    finally:
        if stopped:
            compose("up", "-d", "--wait", "customers")
    assert measure(FEDERATED_REPORT)["rows"] == converged["rows"]
    load("orders", "b2")
    load("customers", "b2")
    assert copied_report() == converged["rows"]
    return dict(initial=initial, mismatch=mismatch, orphan_orders=orphan,
                converged=converged, stale_warehouse_cutoffs=stale_cutoffs,
                caught_up_cutoffs=provenance(), outage_sqlstate=outage_sqlstate,
                connector_config_preserved=True, warehouse_remote_rows_per_read=0,
                local_scan=local_scanned,
                local_execution_ms=local_plan["Execution Time"])


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

将下面的完整代码保存为 `labs/dataflows/analytics/pg.py`；文件已存在时，以本版内容替换该文件。

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

将下面的完整代码保存为 `labs/dataflows/analytics/compose.yaml`；文件已存在时，以本版内容替换该文件。

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

