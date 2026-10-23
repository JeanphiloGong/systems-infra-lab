# Q02 v1: A secondary index is not always cheaper

The table deliberately has 90,000 orders for user 0 and 100 orders for each rare user. Build by_user and compare the rare lookup against the common lookup. PostgreSQL should select an Index Scan or Bitmap Index Scan for user 42 while selecting a Seq Scan for user 0. No enable_seqscan switch forces these decisions.

## Run Against PostgreSQL

Use the repository's isolated PostgreSQL 16 service. From the repository root:

```bash
docker compose -f infra/postgres.compose.yaml up -d
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv sync --locked
```

The checkpoint creates a unique q02_ schema, inserts real orders, gathers statistics, executes real queries and EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON), and drops only its own schema in finally. Save the complete checkpoint at the named path. This checkpoint includes only the setup and experiment for this lesson. psycopg is the only external dependency.

将下面的完整代码保存为 `postgres.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: postgres.py -->

```python
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
            connection.execute("CREATE INDEX by_user ON orders(user_id)")
            plans["selective"] = explain(connection, query)
            common_query = "SELECT id, amount FROM orders WHERE user_id=0 ORDER BY id"
            plans["common"] = explain(connection, common_query)
            assert any("Index" in name for name in measure(plans["selective"])["nodes"])
            assert "Seq Scan" in measure(plans["common"])["nodes"]
            assert connection.execute(query).fetchall() == expected
            assert connection.execute(common_query).fetchall() == [(i, i % 1000) for i in range(1, 90001)]
            return {"server": connection.info.server_version, "metrics": {key: measure(plan) for key, plan in plans.items()}, "plans": plans}
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
```

```bash
uv run python postgres.py
```

## Verify the Result

The selective result must equal the result captured before index creation. Both queries project id and amount and order by id, varying only user_id; many scattered heap visits can cost more than scanning. ANALYZE supplies the data distribution to the planner. Read the actual node names and estimates rather than treating indexes as an unconditional speedup.

The output includes complete plans plus a compact metric projection. Root buffer counts are inclusive of child activity: do not sum them again across the tree. Shared hits are PostgreSQL buffer-cache accesses; shared reads are blocks fetched into that cache, potentially served by the OS cache, not necessarily physical device reads. Execution Time is a local wall-clock sample, not an index performance guarantee. All planner choices are measured on this dataset with parallel query disabled for readable plans; other server settings can affect outcomes.

Optional reference validation (uses the reference checkout and its tutorial text):

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/query/indexes/replay_q02.py --version 1
```

</details>

Replay requires the DSN and fails explicitly if it is missing. It extracts the code above, not current worktree source. The old Python Table example is explanatory only and is not evidence for PostgreSQL behavior.
