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
