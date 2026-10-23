# Q03 v2: Correlation defeats multiplication of selectivities

Build city and zip as identical columns: half the rows have the hot value zero; each rare value appears 500 times. Without cross-column statistics, multiplying rare predicate selectivities estimates about 2 rows when the true count is 500. For the hot pair it estimates 25,000 instead of 50,000. Execute both queries to make the errors visible.

## Read the Evidence

Create dependencies and multivariate MCV statistics on (city,zip), run ANALYZE, and execute the exact predicates again. Assert both estimates improve while actual rows and results stay unchanged. A high column statistics target covers this small dataset to reduce sampling variation; it is not a universal tuning recommendation. This demonstrates statistics appropriate for same-table correlated equality predicates, not a cure for all correlated joins or arbitrary range conditions.

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
uv run python tests/query/planner/replay_q03.py --version 2
```

</details>

The first command runs the file at the indicated checkpoint path; the replay command runs from the repository root and extracts the printed code into an empty directory. No current planner module is imported. Missing DSN is an error, not a successful simulated run.

## What the Measurements Mean

Full JSON EXPLAIN ANALYZE BUFFERS SETTINGS accompanies the summary, including estimated costs, actual rows/loops, timing, and operator memory/spill fields. Root buffers are inclusive: do not sum the same activity again over children. Multiply block counters by the reported block_size for database-layer bytes; shared reads may be served by OS cache, so they are not direct device-I/O counts.

PostgreSQL core EXPLAIN does not report per-query CPU milliseconds. The output therefore reports actual row/loop work and elapsed execution time alongside the server's cpu_tuple_cost, cpu_index_tuple_cost, and cpu_operator_cost assumptions. Those cost parameters are estimates in planner units, not measured CPU time; no invented CPU counter is substituted. Hashing, comparisons, and repeated probes consume CPU, while spill adds temporary I/O. Elapsed time combines these effects and is sensitive to caching and scheduling. No assertion requires a fixed speedup.

The checkpoint freezes observed plan behavior and result invariants on PostgreSQL 16. It does not imply every production workload or optimizer version chooses the same plan.
