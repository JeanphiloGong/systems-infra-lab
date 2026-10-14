# T04 v2：失败的请求必须重新判断

v1让数据库中止不可串行历史，却没有完成被中止的业务请求。若直接重复旧的“可以下班”决定，仍可能让最后一人离开。本版重试的是完整事务：新快照、新人数、新判断。

## 1. 保留同一个竞争场景

两个医生初始都在岗。两个连接都在SERIALIZABLE事务中读取人数2，用Barrier(2)保证两次读取先完成，再各自更新。一个事务成功，另一个可能在UPDATE或COMMIT收到SerializationFailure；catch必须在with transaction之外，使两种失败都被捕获并完成回滚。

## 2. 有限次重试完整业务操作

新增retry_once，返回(重试次数, 是否允许下班)。max_retries=3表示初始尝试外最多再试三次；负数拒绝，耗尽后原异常向上传播。只捕获SerializationFailure，连接错误或业务异常不伪装成可重试冲突。

屏障只能用于首次尝试。胜者完成后不再参加屏障，如果失败者重试仍等待两人，会永远等不到另一方。于是仅retries==0进入barrier。重试的新SELECT看到人数1，allowed=False，不执行更新但正常提交；拒绝下班是业务结果，不是数据库失败。

concurrent_retry给两个工作线程各一个独立连接，汇总实际结果。通常是[(0, True), (1, False)]或相反顺序，不固定哪个医生获胜。最终只有一人下班，与v0的串行参考一致。这里没有sleep、预制异常或无竞争的替代测试。

## 3. 冻结完整重试检查点

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true")
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
            print(concurrent_retry(first, second) if args.retry else concurrent_once(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.serializable.serializable --retry
```

输出两名医生的(重试次数,业务决定)，检查重试总数至少1、恰好一个True和一个False。也可运行不带参数的v1对照，仍得到(1,1)。

现在冻结本版。下一版在相同冲突场景中累计吞吐和重试指标。
