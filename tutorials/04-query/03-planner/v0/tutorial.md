# Q03 v0: A table grows; the best access path changes

Run the same user_id=7 predicate and create the same B-tree for a 20-row and a 100,000-row table. A one-page table can be cheaper to scan than to enter an index. At larger scale, a bitmap heap/index path can touch only matching pages. Both experiments retain a correct reference result generated from the fixture.

## Read the Evidence

Read Plan Rows separately from Actual Rows and Total Cost separately from Execution Time. The same predicate is compared at two scales, not two forced strategies. PostgreSQL remains free to choose; the assertions target the pinned PostgreSQL 16 configuration. A different server cost configuration can change the outcome.

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
uv run python tests/query/planner/replay_q03.py --version 0
```

The first command runs the file at the indicated checkpoint path; the replay command runs from the repository root and extracts the printed code into an empty directory. No current planner module is imported. Missing DSN is an error, not a successful simulated run.

## What the Measurements Mean

Full JSON EXPLAIN ANALYZE BUFFERS SETTINGS accompanies the summary, including estimated costs, actual rows/loops, timing, and operator memory/spill fields. Root buffers are inclusive: do not sum the same activity again over children. Multiply block counters by the reported block_size for database-layer bytes; shared reads may be served by OS cache, so they are not direct device-I/O counts.

PostgreSQL core EXPLAIN does not report per-query CPU milliseconds. The output therefore reports actual row/loop work and elapsed execution time alongside the server's cpu_tuple_cost, cpu_index_tuple_cost, and cpu_operator_cost assumptions. Those cost parameters are estimates in planner units, not measured CPU time; no invented CPU counter is substituted. Hashing, comparisons, and repeated probes consume CPU, while spill adds temporary I/O. Elapsed time combines these effects and is sensitive to caching and scheduling. No assertion requires a fixed speedup.

The checkpoint freezes observed plan behavior and result invariants on PostgreSQL 16. It does not imply every production workload or optimizer version chooses the same plan.
