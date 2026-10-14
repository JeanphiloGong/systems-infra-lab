"""PostgreSQL plans, buffer accesses, and visibility experiments."""
import json
import os
from uuid import uuid4

import psycopg
from psycopg import sql


def nodes(plan):
    yield plan
    for child in plan.get("Plans", []):
        yield from nodes(child)


def explain(connection, query):
    document = connection.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query).fetchone()[0][0]
    return document


def measure(document):
    plan = document["Plan"]
    return {
        "nodes": [node["Node Type"] for node in nodes(plan)],
        "estimated_rows": plan["Plan Rows"],
        "actual_rows": plan["Actual Rows"],
        "shared_hit_blocks": plan.get("Shared Hit Blocks", 0),
        "shared_read_blocks": plan.get("Shared Read Blocks", 0),
        "buffer_accesses": plan.get("Shared Hit Blocks", 0) + plan.get("Shared Read Blocks", 0),
        "heap_fetches": sum(node.get("Heap Fetches", 0) for node in nodes(plan)),
        "execution_ms": document["Execution Time"],
    }


def run():
    schema = "q02_" + uuid4().hex
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            connection.execute("SET max_parallel_workers_per_gather=0")
            connection.execute("CREATE TABLE orders (id int, user_id int, created_at int, amount int, payload text) WITH (autovacuum_enabled=false)")
            connection.execute("INSERT INTO orders SELECT i, CASE WHEN i <= 90000 THEN 0 ELSE 1 + i % 100 END, i, i % 1000, repeat('x',200) FROM generate_series(1,100000) i")
            connection.execute("ANALYZE orders")
            query = "SELECT id, amount FROM orders WHERE user_id=42 ORDER BY id"
            expected = connection.execute(query).fetchall()
            plans = {"baseline": explain(connection, query)}
            assert "Seq Scan" in measure(plans["baseline"])["nodes"]
            return {"server": connection.info.server_version, "metrics": {key: measure(plan) for key, plan in plans.items()}, "plans": plans}
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
