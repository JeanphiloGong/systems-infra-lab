# Q04 v4：失效之后，旧查询还可能把缓存填脏

构造确定性的两个执行流。后台 reader 查询 PostgreSQL 得到 300,000 后，用 Event 暂停在填缓存之前；主线程 writer 提交增加 50 的 INSERT，再失效缓存；放行 reader，它仍可能把旧结果写回。naive 分支确实返回旧值，直到 TTL 边界再次回源。

## 从缺口到实现

guarded 分支在回源前记录缓存 epoch，失效时增加 epoch。结果返回后，在同一个锁下比较 epoch 与填缓存；不一致就丢弃这次填充并重新查询。真实 reader 连接是 autocommit，每次 SELECT 取得新的 READ COMMITTED 快照，所以重试能读到新提交数据。断言旧填充被拒一次，源查询确实重试，返回 300,050。所有跨线程等待有期限，writer 即使失败也会释放 reader。

## 本版完整检查点

以下文件全部列出，可在空目录重建。数据源是仓库的独立 PostgreSQL 16 服务；每次运行创建随机 q04_ schema，finally 删除自己的对象。只有数据库依赖 psycopg，没有从工作树偷取隐藏实现。先在仓库根目录准备环境：

```bash
docker compose -f infra/postgres.compose.yaml up -d
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv sync --locked
```

common.py 负责隔离数据和清理；实验入口使用其提供的真实连接。

将下面的完整代码保存为 `labs/query/derived/common.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/query/derived/common.py -->

```python
import os
from contextlib import contextmanager
from uuid import uuid4

import psycopg
from psycopg import sql


@contextmanager
def database():
    schema = "q04_" + uuid4().hex
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            connection.execute("SET statement_timeout='10s'")
            connection.execute("CREATE TABLE sales (id int PRIMARY KEY, day int NOT NULL, amount int NOT NULL)")
            connection.execute("INSERT INTO sales SELECT i,i%30,10 FROM generate_series(1,30000) i")
            connection.execute("ANALYZE sales")
            yield connection, schema
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def total(connection):
    return connection.execute("SELECT sum(amount) FROM sales").fetchone()[0]


def plan(connection, query):
    return connection.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query).fetchone()[0][0]


def summary(document):
    node = document["Plan"]
    return {"rows": node["Actual Rows"], "elapsed_ms": document["Execution Time"],
            "shared_hits": node.get("Shared Hit Blocks", 0), "shared_reads": node.get("Shared Read Blocks", 0)}
```

将下面的完整代码保存为 `labs/query/derived/cache.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/query/derived/cache.py -->

```python
from threading import Lock


class Cache:
    """One key, one process; a monotonic caller clock makes tests deterministic."""

    def __init__(self, clock, ttl=5):
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.clock, self.ttl = clock, ttl
        self.entry = None
        self.epoch = 0
        self.lock = Lock()
        self.hits = self.loads = self.rejected_fills = 0

    def invalidate(self):
        with self.lock:
            self.epoch += 1
            self.entry = None

    def get(self, loader, after_load=None, guarded=True):
        while True:
            with self.lock:
                if self.entry is not None and self.clock() < self.entry[1]:
                    self.hits += 1
                    return self.entry[0]
                epoch = self.epoch
            value = loader()
            self.loads += 1
            if after_load is not None:
                after_load()
                after_load = None
            with self.lock:
                if guarded and epoch != self.epoch:
                    self.rejected_fills += 1
                    continue
                self.entry = (value, self.clock() + self.ttl)
                return value
```

将下面的完整代码保存为 `labs/query/derived/v4.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/query/derived/v4.py -->

```python
from concurrent.futures import ThreadPoolExecutor
import json
import os
from threading import Event

import psycopg
from psycopg import sql

from labs.query.derived.cache import Cache
from labs.query.derived.common import database, total


def run():
    outcomes = {}
    for guarded in (False, True):
        with database() as (writer, schema):
            now = [0.0]
            cache = Cache(lambda: now[0])
            captured, release = Event(), Event()

            def read():
                with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as reader:
                    reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))

                    def pause():
                        captured.set()
                        if not release.wait(5):
                            raise TimeoutError("writer did not release the paused fill")

                    return cache.get(lambda: total(reader), after_load=pause, guarded=guarded)

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(read)
                try:
                    assert captured.wait(5)
                    writer.execute("INSERT INTO sales VALUES (30001,0,50)")
                    committed_at = now[0]
                    # The SQL commit has completed before this invalidation.
                    cache.invalidate()
                finally:
                    release.set()
                returned = future.result(timeout=10)
            actual = total(writer)
            assert actual == 300050
            now[0] = 4.999
            before_expiry = cache.get(lambda: total(writer))
            now[0] = 5
            after_expiry = cache.get(lambda: total(writer))
            if guarded:
                assert returned == before_expiry == after_expiry == actual
                assert cache.rejected_fills == 1
            else:
                assert returned == before_expiry == 300000 and after_expiry == actual
            outcomes["epoch_guard" if guarded else "naive"] = {
                "returned": returned, "source": actual, "before_expiry": before_expiry,
                "after_expiry": after_expiry, "rejected_fills": cache.rejected_fills,
                "stale_window_in_this_schedule_seconds": 0 if returned == actual else now[0] - committed_at,
                "loads": cache.loads,
            }
    with database() as (writer, _):
        now = [0.0]
        cache = Cache(lambda: now[0])
        assert cache.get(lambda: total(writer)) == 300000
        now[0] = 1
        writer.execute("INSERT INTO sales VALUES (30001,0,50)")
        committed_at = now[0]
        assert cache.get(lambda: total(writer)) == 300000
        now[0] = 2
        cache.invalidate()
        assert cache.get(lambda: total(writer)) == 300050
        outcomes["commit_to_invalidation_gap"] = {
            "observed_logical_seconds": now[0] - committed_at,
            "old_read_during_gap": 300000, "after_invalidation": 300050,
        }
    return outcomes


if __name__ == "__main__":
    print(json.dumps(run()))
```

在仓库根目录或重建后的目录，执行实验模块；独立回放命令从仓库根目录执行：

```bash
uv run python -m labs.query.derived.v4
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/query/derived/replay_q04.py --version 4
```

</details>

## 验证与边界

记录调度内的旧读窗口：naive 从提交时刻 0 到 TTL 时刻 5，guarded 在本调度中为 0。另一个独立实验专门让提交发生在逻辑时刻 1、失效在 2，二者之间仍可命中旧值，测得一秒残余窗口。这个数是受控逻辑时钟下的观测，不是生产延迟承诺。epoch 只在同一进程且所有写入都执行失效时成立；进程崩溃丢失失效、外部写入、失效消息延迟、长事务快照、不断写入导致重试饥饿，都不由本最小实现解决。不能把“本次安全填充”推广为强一致或零旧读窗口。

回放将本页所有 checkpoint 文件写入新的临时目录，PYTHONPATH 仅指向该目录，再启动独立解释器执行对应版本。缺少 DSN 时明确失败，不以跳过冒充成功。数据库 buffer hit/read 是 PostgreSQL 层的访问，不直接等于物理设备 I/O；EXPLAIN 的耗时为本机采样，不能替代容量测试。逻辑 TTL 时钟与数据库锁等待的墙钟测量分别命名，避免混淆。
