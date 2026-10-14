# Q02 v2: Compare column order with the same range and sort

The requirement is user 42, created_at in [90000,100000), latest 20 first. Execute that exact SQL with (user_id,created_at), remove the candidate index, then execute it with (created_at,user_id). Both ordered B-trees can return descending timestamps without an explicit Sort, but only the first groups the selected user into one narrow interval.

## Run Against PostgreSQL

Use the repository's isolated PostgreSQL 16 service. From the repository root:

```bash
docker compose -f infra/postgres.compose.yaml up -d
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv sync --locked
```

The checkpoint creates a unique q02_ schema, inserts real orders, gathers statistics, executes real queries and EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON), and drops only its own schema in finally. Save the complete checkpoint at the named path. This checkpoint includes only the setup and experiment for this lesson. psycopg is the only external dependency.

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
            query = "SELECT id, created_at FROM orders WHERE user_id=42 AND created_at>=90000 AND created_at<100000 ORDER BY created_at DESC LIMIT 20"
            expected = connection.execute(query).fetchall()
            for name, columns in (("user_time", "user_id,created_at"), ("time_user", "created_at,user_id")):
                connection.execute(sql.SQL("CREATE INDEX candidate ON orders ({})").format(sql.SQL(columns)))
                plans[name] = explain(connection, query)
                assert connection.execute(query).fetchall() == expected
                assert any("Index" in node for node in measure(plans[name])["nodes"])
                connection.execute("DROP INDEX candidate")
            assert measure(plans["user_time"])["buffer_accesses"] < measure(plans["time_user"])["buffer_accesses"]
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

Both result sets must equal the baseline range/sort result. Assert both use index access and compare total shared buffer hits plus reads, avoiding cache-state artifacts from comparing hits alone. PostgreSQL does not expose every internal index-entry comparison in EXPLAIN; buffer accesses are the measured work proxy here. Planner choices and skip-scan support vary across releases, so this experiment targets the pinned PostgreSQL 16 fixture.

The output includes complete plans plus a compact metric projection. Root buffer counts are inclusive of child activity: do not sum them again across the tree. Shared hits are PostgreSQL buffer-cache accesses; shared reads are blocks fetched into that cache, potentially served by the OS cache, not necessarily physical device reads. Execution Time is a local wall-clock sample, not an index performance guarantee. All planner choices are measured on this dataset with parallel query disabled for readable plans; other server settings can affect outcomes.

Strictly replay this printed checkpoint in a temporary directory:

```bash
uv run python tests/query/indexes/replay_q02.py --version 2
```

Replay requires the DSN and fails explicitly if it is missing. It extracts the code above, not current worktree source. The old Python Table example is explanatory only and is not evidence for PostgreSQL behavior.
