# Q03 v1: Stale statistics hide a new hotspot

First distribute 100,000 rows uniformly across 1,000 users, create the index, and ANALYZE. Then change 90,000 rows to user 7 without analyzing again. Autovacuum is disabled on this disposable table so an asynchronous ANALYZE cannot erase the demonstration. The query now returns 90,010 rows, yet column statistics describe the old distribution.

## Read the Evidence

Capture a real indexed stale plan, execute ANALYZE, then capture the same SQL again. Assert the refreshed row estimate is closer and that a sequential scan replaces the indexed plan. Also compare complete sorted results: ANALYZE may change the plan, never the answer. Relation size estimates can still change before ANALYZE; stale means old column-distribution statistics, not frozen metadata. The new plan is not guaranteed faster in one warm-cache sample: in our first run it was slower. Cost-based choice and elapsed time are different evidence.

This is an actual PostgreSQL experiment, not the older explanatory cost model. Each checkpoint creates a unique q03_ schema and removes it in finally. Parallel query and JIT are disabled locally to make operator work easier to compare; SQL execution is bounded by a 30-second statement timeout. The role needs schema/table creation and ANALYZE/VACUUM privileges on its own objects.

## Complete Checkpoint

Start the isolated service and export its DSN from the repository root:

```bash
docker compose -f infra/postgres.compose.yaml up -d
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv sync --locked
```

This version-specific file contains only this experiment and its plan-reading helpers:

将下面的完整代码保存为 `postgres.py`；文件已存在时，以本版内容替换该文件。

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
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/query/planner/replay_q03.py --version 1
```

</details>

The first command runs the file at the indicated checkpoint path; the replay command runs from the repository root and extracts the printed code into an empty directory. No current planner module is imported. Missing DSN is an error, not a successful simulated run.

## What the Measurements Mean

Full JSON EXPLAIN ANALYZE BUFFERS SETTINGS accompanies the summary, including estimated costs, actual rows/loops, timing, and operator memory/spill fields. Root buffers are inclusive: do not sum the same activity again over children. Multiply block counters by the reported block_size for database-layer bytes; shared reads may be served by OS cache, so they are not direct device-I/O counts.

PostgreSQL core EXPLAIN does not report per-query CPU milliseconds. The output therefore reports actual row/loop work and elapsed execution time alongside the server's cpu_tuple_cost, cpu_index_tuple_cost, and cpu_operator_cost assumptions. Those cost parameters are estimates in planner units, not measured CPU time; no invented CPU counter is substituted. Hashing, comparisons, and repeated probes consume CPU, while spill adds temporary I/O. Elapsed time combines these effects and is sensitive to caching and scheduling. No assertion requires a fixed speedup.

The checkpoint freezes observed plan behavior and result invariants on PostgreSQL 16. It does not imply every production workload or optimizer version chooses the same plan.
