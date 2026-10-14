"""PostgreSQL plans, buffer accesses, and visibility experiments."""
import json
import os
import sys
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


def run(version):
    if version not in range(4):
        raise ValueError("version must be 0..3")
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
            if version == 1:
                connection.execute("CREATE INDEX by_user ON orders(user_id)")
                plans["selective"] = explain(connection, query)
                common_query = "SELECT id, amount FROM orders WHERE user_id=0 ORDER BY id"
                plans["common"] = explain(connection, common_query)
                assert any("Index" in name for name in measure(plans["selective"])["nodes"])
                assert "Seq Scan" in measure(plans["common"])["nodes"]
                assert connection.execute(query).fetchall() == expected
                assert connection.execute(common_query).fetchall() == [(i, i % 1000) for i in range(1, 90001)]
            if version == 2:
                query = "SELECT id, created_at FROM orders WHERE user_id=42 AND created_at>=90000 AND created_at<100000 ORDER BY created_at DESC LIMIT 20"
                expected = connection.execute(query).fetchall()
                for name, columns in (("user_time", "user_id,created_at"), ("time_user", "created_at,user_id")):
                    connection.execute(sql.SQL("CREATE INDEX candidate ON orders ({})").format(sql.SQL(columns)))
                    plans[name] = explain(connection, query)
                    assert connection.execute(query).fetchall() == expected
                    assert any("Index" in node for node in measure(plans[name])["nodes"])
                    connection.execute("DROP INDEX candidate")
                assert measure(plans["user_time"])["buffer_accesses"] < measure(plans["time_user"])["buffer_accesses"]
            if version == 3:
                connection.execute("CREATE INDEX covering ON orders(user_id, created_at) INCLUDE (amount)")
                connection.execute("VACUUM (ANALYZE) orders")
                query = "SELECT user_id, created_at, amount FROM orders WHERE user_id=42 ORDER BY created_at"
                before = connection.execute(query).fetchall()
                plans["visible"] = explain(connection, query)
                connection.execute("UPDATE orders SET amount=amount+1 WHERE user_id=42")
                plans["updated"] = explain(connection, query)
                changed = connection.execute(query).fetchall()
                assert changed == [(u, t, amount + 1) for u, t, amount in before]
                connection.execute("VACUUM (FULL, ANALYZE) orders")
                connection.execute("VACUUM (ANALYZE) orders")
                plans["vacuumed"] = explain(connection, query)
                assert connection.execute(query).fetchall() == changed
                for name in ("visible", "updated", "vacuumed"):
                    assert "Index Only Scan" in measure(plans[name])["nodes"]
                assert measure(plans["visible"])["heap_fetches"] == 0
                assert measure(plans["updated"])["heap_fetches"] > 0
                assert measure(plans["vacuumed"])["heap_fetches"] == 0
            return {"server": connection.info.server_version, "metrics": {key: measure(plan) for key, plan in plans.items()}, "plans": plans}
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    print(json.dumps(run(int(sys.argv[1])), indent=2))
