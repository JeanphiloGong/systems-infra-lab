# T04 v3：让竞争成本成为可检查的报告

v2完成真实中止后的重试，但一次成功不能回答重试成本。本版在同一临时schema中运行十轮相同竞争，每轮先将两人重置为在岗。模型固定两连接和两请求，目的是测量已知竞争机制，不模拟完整线上流量。

## 1. 给测量定义分母

新增measure_once，rounds默认10，必须正数。每轮调用v2的concurrent_retry，因此20个业务操作最终都有数据库事务正常提交，其中10个允许下班、10个拒绝。committed包含没有UPDATE的正常拒绝事务，不能理解成20人都下班。

aborted_attempts累加遇到的SerializationFailure；本实验所有失败尝试都在预算内重试，所以retries与它相等。若耗尽预算则整个测量抛错，不发布一份伪装完整的报告。remaining记录最后一轮在岗人数。

## 2. 接入真实命令

monotonic测量整个循环，包含重置SQL、线程创建、等待和重试。operations_per_second是20/elapsed，不是数据库纯UPDATE吞吐。main新增--metrics分支调用measure_once，--retry继续保留v2行为。

比较实验应保存Python/PostgreSQL版本、CPU、连接数、rounds以及多次运行结果；本课不承诺固定毫秒或QPS，也不把十轮小样本叫性能基准。可串行化允许某个等价串行顺序；strict serializability还要求与非重叠操作的实时先后相容。此处只验证值班约束及重试轨迹，没有证明跨节点实时一致性。

## 3. 冻结完整测量检查点

前置上一版。所有命令在仓库根目录运行，数据库仅指向本仓库临时实例：

```bash
uv sync --locked
docker compose -f infra/postgres.compose.yaml up -d --wait
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
```

保留完整 `labs/transactions/serializable/schema.sql`：

```sql
CREATE TABLE doctors (id integer PRIMARY KEY, on_call boolean NOT NULL);
INSERT INTO doctors VALUES (1, true), (2, true);
```

下面完整替换 `labs/transactions/serializable/serializable.py`。唯一schema、statement_timeout和finally清理沿用v1；本版没有隐藏源文件依赖。

<!-- checkpoint: labs/transactions/serializable/serializable.py -->

```python
from __future__ import annotations

import argparse
import os
from time import monotonic
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg import sql


def leave(conn: psycopg.Connection, doctor: int, barrier: Barrier | None = None) -> bool:
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            count = conn.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
            if barrier is not None:
                barrier.wait(timeout=5)
            if count > 1:
                conn.execute("UPDATE doctors SET on_call=false WHERE id=%s", (doctor,))
        return True
    except psycopg.errors.SerializationFailure:
        return False


def concurrent_once(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int]:
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(leave, first, 1, barrier), pool.submit(leave, second, 2, barrier)]
        outcomes = [future.result(timeout=12) for future in results]
    return outcomes.count(False), first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]


def retry_once(
    conn: psycopg.Connection,
    doctor: int,
    max_retries: int = 3,
    barrier: Barrier | None = None,
) -> tuple[int, bool]:
    if max_retries < 0:
        raise ValueError("max_retries must be nonnegative")
    retries = 0
    while True:
        try:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                count = conn.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
                allowed = count > 1
                if retries == 0 and barrier is not None:
                    barrier.wait(timeout=5)
                if allowed:
                    conn.execute("UPDATE doctors SET on_call=false WHERE id=%s", (doctor,))
            return retries, allowed
        except psycopg.errors.SerializationFailure:
            retries += 1
            if retries > max_retries:
                raise


def concurrent_retry(
    first: psycopg.Connection, second: psycopg.Connection,
) -> list[tuple[int, bool]]:
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(retry_once, first, 1, 3, barrier),
            pool.submit(retry_once, second, 2, 3, barrier),
        ]
        return [future.result(timeout=12) for future in futures]


def measure_once(
    first: psycopg.Connection, second: psycopg.Connection, rounds: int = 10,
) -> dict[str, float | int]:
    if rounds < 1:
        raise ValueError("rounds must be positive")
    retries = allowed = 0
    started = monotonic()
    for _ in range(rounds):
        first.execute("UPDATE doctors SET on_call=true")
        outcomes = concurrent_retry(first, second)
        retries += sum(count for count, _ in outcomes)
        allowed += sum(decision for _, decision in outcomes)
    elapsed = monotonic() - started
    remaining = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
    return {
        "operations": rounds * 2, "committed": rounds * 2,
        "aborted_attempts": retries, "retries": retries,
        "allowed": allowed, "refused": rounds * 2 - allowed,
        "remaining": remaining, "elapsed_seconds": elapsed,
        "operations_per_second": rounds * 2 / elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t04_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            if args.metrics:
                print(measure_once(first, second))
            else:
                print(concurrent_retry(first, second) if args.retry else concurrent_once(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.serializable.serializable --metrics
```

输出报告应有operations=20、committed=20、allowed=10、refused=10、remaining=1，retries至少10，elapsed_seconds和operations_per_second为本次实际值。不能把打印键名存在当作指标实验通过，必须核对这些关系。

现在冻结本版。负载结果仅支持此两连接、十轮、明确初始化的模型；更复杂负载需要另设业务不变量和预算。
