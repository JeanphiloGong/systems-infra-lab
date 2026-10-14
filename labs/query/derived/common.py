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
