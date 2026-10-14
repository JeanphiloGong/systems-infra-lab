# Q03 v3: Join work and sort spill have different resource costs

The same 40,000-order join is executed with nested-loop and hash alternatives. Local enable_* switches are diagnostic controls that discourage other join strategies, not a production tuning recommendation. Inspect the resulting node names and compare the full result sets. The nested-loop plan may add Memoize, so actual inner scan loops can be much smaller than outer rows. The hash plan reports its hash-table memory and batches.

## Read the Evidence

Then sort the same wide rows with 64kB and 64MB work_mem. Assert an external merge with actual temporary reads/writes in the first case and an in-memory sort without temporary writes in the second. Both must match the complete ordered reference result. Sort Space Used is in kB and refers to memory or disk according to Sort Space Type; Temp Read/Written Blocks count cumulative temporary I/O and can exceed peak spill size across merge passes. work_mem is per eligible operation, not a process memory cap.

This is an actual PostgreSQL experiment, not the older explanatory cost model. Each checkpoint creates a unique q03_ schema and removes it in finally. Parallel query and JIT are disabled locally to make operator work easier to compare; SQL execution is bounded by a 30-second statement timeout. The role needs schema/table creation and ANALYZE/VACUUM privileges on its own objects.

## Complete Checkpoint

Start the isolated service and export its DSN from the repository root:

```bash
docker compose -f infra/postgres.compose.yaml up -d
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv sync --locked
```

This version-specific file contains only this experiment and its plan-reading helpers:

<!-- checkpoint: postgres.py -->

```python
"""Measured PostgreSQL planner experiments; requires the isolated lab DSN."""
import json
import os
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


def run():
    schema = "q03_" + uuid4().hex
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as c:
        c.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            c.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            c.execute("SET max_parallel_workers_per_gather=0")
            c.execute("SET jit=off")
            c.execute("SET statement_timeout='30s'")
            plans = {}
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
    print(json.dumps(run(), indent=2))
```

```bash
uv run python postgres.py
uv run python tests/query/planner/replay_q03.py --version 3
```

The first command runs the file at the indicated checkpoint path; the replay command runs from the repository root and extracts the printed code into an empty directory. No current planner module is imported. Missing DSN is an error, not a successful simulated run.

## What the Measurements Mean

Full JSON EXPLAIN ANALYZE BUFFERS SETTINGS accompanies the summary, including estimated costs, actual rows/loops, timing, and operator memory/spill fields. Root buffers are inclusive: do not sum the same activity again over children. Multiply block counters by the reported block_size for database-layer bytes; shared reads may be served by OS cache, so they are not direct device-I/O counts.

PostgreSQL core EXPLAIN does not report per-query CPU milliseconds. The output therefore reports actual row/loop work and elapsed execution time alongside the server's cpu_tuple_cost, cpu_index_tuple_cost, and cpu_operator_cost assumptions. Those cost parameters are estimates in planner units, not measured CPU time; no invented CPU counter is substituted. Hashing, comparisons, and repeated probes consume CPU, while spill adds temporary I/O. Elapsed time combines these effects and is sensitive to caching and scheduling. No assertion requires a fixed speedup.

The checkpoint freezes observed plan behavior and result invariants on PostgreSQL 16. It does not imply every production workload or optimizer version chooses the same plan.
