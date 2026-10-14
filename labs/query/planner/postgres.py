"""Measured PostgreSQL planner experiments; requires the isolated lab DSN."""
import json
import os
import sys
from uuid import uuid4

import psycopg
from psycopg import sql


def walk(plan):
    yield plan
    for child in plan.get("Plans", []):
        yield from walk(child)


def explain(connection, query):
    return connection.execute("EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON) " + query).fetchone()[0][0]


def metrics(document):
    plan = document["Plan"]
    return {
        "nodes": [n["Node Type"] for n in walk(plan)],
        "estimated_rows": plan["Plan Rows"], "actual_rows": plan["Actual Rows"],
        "total_cost": plan["Total Cost"], "execution_ms": document["Execution Time"],
        "shared_hit_blocks": plan.get("Shared Hit Blocks", 0),
        "shared_read_blocks": plan.get("Shared Read Blocks", 0),
        "temp_read_blocks": plan.get("Temp Read Blocks", 0),
        "temp_written_blocks": plan.get("Temp Written Blocks", 0),
        "operators": [{key: n[key] for key in (
            "Node Type", "Plan Rows", "Actual Rows", "Actual Loops", "Actual Total Time",
            "Sort Method", "Sort Space Used", "Sort Space Type", "Peak Memory Usage", "Hash Batches"
        ) if key in n} for n in walk(plan)],
    }


def run(version):
    if version not in range(4):
        raise ValueError("version must be 0..3")
    schema = "q03_" + uuid4().hex
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as c:
        c.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            c.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            c.execute("SET max_parallel_workers_per_gather=0")
            c.execute("SET jit=off")
            c.execute("SET statement_timeout='30s'")
            plans = {}
            if version == 0:
                for label, size in (("small", 20), ("large", 100000)):
                    c.execute("CREATE TABLE orders (id int, user_id int, payload text) WITH (autovacuum_enabled=false)")
                    c.execute("INSERT INTO orders SELECT i,i%%1000,repeat('x',200) FROM generate_series(1,%s) i", (size,))
                    c.execute("CREATE INDEX by_user ON orders(user_id)")
                    c.execute("ANALYZE orders")
                    query = "SELECT id FROM orders WHERE user_id=7"
                    plans[label] = explain(c, query)
                    assert sorted(c.execute(query).fetchall()) == [(i,) for i in range(1, size + 1) if i % 1000 == 7]
                    c.execute("DROP TABLE orders")
                assert "Seq Scan" in metrics(plans["small"])["nodes"]
                assert any("Index" in name for name in metrics(plans["large"])["nodes"])
            elif version == 1:
                c.execute("CREATE TABLE orders (id int, user_id int, payload text) WITH (autovacuum_enabled=false)")
                c.execute("INSERT INTO orders SELECT i,i%1000,repeat('x',200) FROM generate_series(1,100000) i")
                c.execute("CREATE INDEX by_user ON orders(user_id)")
                c.execute("ANALYZE orders")
                c.execute("UPDATE orders SET user_id=7 WHERE id<=90000")
                query = "SELECT id FROM orders WHERE user_id=7"
                expected = sorted(c.execute(query).fetchall())
                plans["stale"] = explain(c, query)
                c.execute("ANALYZE orders")
                plans["analyzed"] = explain(c, query)
                assert sorted(c.execute(query).fetchall()) == expected
                assert any("Index" in name for name in metrics(plans["stale"])["nodes"])
                assert "Seq Scan" in metrics(plans["analyzed"])["nodes"]
                actual = plans["analyzed"]["Plan"]["Actual Rows"]
                assert abs(plans["analyzed"]["Plan"]["Plan Rows"] - actual) < abs(plans["stale"]["Plan"]["Plan Rows"] - actual)
            elif version == 2:
                c.execute("CREATE TABLE orders (id int, city int, zip int) WITH (autovacuum_enabled=false)")
                c.execute("INSERT INTO orders SELECT i,CASE WHEN i<=50000 THEN 0 ELSE 1+i%100 END,CASE WHEN i<=50000 THEN 0 ELSE 1+i%100 END FROM generate_series(1,100000) i")
                c.execute("ALTER TABLE orders ALTER city SET STATISTICS 1000")
                c.execute("ALTER TABLE orders ALTER zip SET STATISTICS 1000")
                c.execute("ANALYZE orders")
                rare = "SELECT id FROM orders WHERE city=42 AND zip=42"
                hot = "SELECT id FROM orders WHERE city=0 AND zip=0"
                plans["independent_rare"] = explain(c, rare)
                plans["independent_hot"] = explain(c, hot)
                expected = c.execute(rare).fetchall()
                c.execute("CREATE STATISTICS city_zip (dependencies,mcv) ON city,zip FROM orders")
                c.execute("ANALYZE orders")
                plans["extended_rare"] = explain(c, rare)
                plans["extended_hot"] = explain(c, hot)
                assert c.execute(rare).fetchall() == expected
                for suffix in ("rare", "hot"):
                    before = plans["independent_" + suffix]["Plan"]
                    after = plans["extended_" + suffix]["Plan"]
                    assert before["Actual Rows"] == after["Actual Rows"]
                    assert abs(after["Plan Rows"] - after["Actual Rows"]) < abs(before["Plan Rows"] - before["Actual Rows"])
            else:
                c.execute("CREATE TABLE customers (id int PRIMARY KEY)")
                c.execute("INSERT INTO customers SELECT i FROM generate_series(1,2000) i")
                c.execute("CREATE TABLE orders (id int, customer_id int, payload text)")
                c.execute("INSERT INTO orders SELECT i,1+i%2000,repeat(md5(i::text),8) FROM generate_series(1,40000) i")
                c.execute("CREATE INDEX order_customer ON orders(customer_id)")
                c.execute("ANALYZE customers")
                c.execute("ANALYZE orders")
                query = "SELECT o.id,c.id FROM orders o JOIN customers c ON c.id=o.customer_id"
                c.execute("SET work_mem='64MB'")
                c.execute("SET enable_mergejoin=off")
                c.execute("SET enable_hashjoin=off")
                plans["nested_loop"] = explain(c, query)
                expected = sorted(c.execute(query).fetchall())
                c.execute("SET enable_hashjoin=on")
                c.execute("SET enable_nestloop=off")
                plans["hash_join"] = explain(c, query)
                assert sorted(c.execute(query).fetchall()) == expected
                assert "Nested Loop" in metrics(plans["nested_loop"])["nodes"]
                assert "Hash Join" in metrics(plans["hash_join"])["nodes"]
                c.execute("RESET enable_nestloop")
                c.execute("RESET enable_mergejoin")
                sort_query = "SELECT id,payload FROM orders ORDER BY payload,id"
                expected = c.execute(sort_query).fetchall()
                c.execute("SET work_mem='64kB'")
                plans["spilled_sort"] = explain(c, sort_query)
                assert c.execute(sort_query).fetchall() == expected
                c.execute("SET work_mem='64MB'")
                plans["memory_sort"] = explain(c, sort_query)
                assert c.execute(sort_query).fetchall() == expected
                assert plans["spilled_sort"]["Plan"]["Sort Space Type"] == "Disk"
                assert plans["memory_sort"]["Plan"]["Sort Space Type"] == "Memory"
                assert metrics(plans["spilled_sort"])["temp_written_blocks"] > 0
                assert metrics(plans["spilled_sort"])["temp_read_blocks"] > 0
                assert metrics(plans["memory_sort"])["temp_written_blocks"] == 0
            return {"server": c.info.server_version, "block_size": int(c.execute("SHOW block_size").fetchone()[0]),
                    "cpu_parameters": {name: c.execute(sql.SQL("SHOW {}").format(sql.Identifier(name))).fetchone()[0]
                                       for name in ("cpu_tuple_cost", "cpu_index_tuple_cost", "cpu_operator_cost")},
                    "metrics": {name: metrics(plan) for name, plan in plans.items()}, "plans": plans}
        finally:
            c.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    print(json.dumps(run(int(sys.argv[1])), indent=2))
