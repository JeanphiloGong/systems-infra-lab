# Q04 v3：Cache-aside：先定义过期边界，再谈命中率

读取销售总额，首次未命中才查询真实数据库；同一时刻再次读取命中。随后源表增加 50，缓存仍允许在五秒 TTL 内返回 300,000。在精确到期点，缓存重新回源并返回 300,050。

## 从缺口到实现

Cache 保存一个聚合键的值、截止时间与版本，get 在锁内检查有效期，回源时不持锁。时钟是注入的单调逻辑时钟，测试不靠 sleep。ttl 从成功填充时刻开始；它限制驻留期限，不是任意事务或暂停时间下的严格源数据年龄上限。当前版本只用 TTL 分支，版本字段为下一版失效竞态做共享实现准备；不是跨进程缓存服务。

## 本版完整检查点

以下文件全部列出，可在空目录重建。数据源是仓库的独立 PostgreSQL 16 服务；每次运行创建随机 q04_ schema，finally 删除自己的对象。只有数据库依赖 psycopg，没有从工作树偷取隐藏实现。先在仓库根目录准备环境：

```bash
docker compose -f infra/postgres.compose.yaml up -d
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
uv sync --locked
```

common.py 负责隔离数据和清理；实验入口使用其提供的真实连接。

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

<!-- checkpoint: labs/query/derived/v3.py -->

```python
import json

from labs.query.derived.cache import Cache
from labs.query.derived.common import database, total


def run():
    with database() as (c, _):
        now = [0.0]
        cache = Cache(lambda: now[0])
        assert cache.get(lambda: total(c)) == 300000
        assert cache.get(lambda: total(c)) == 300000
        c.execute("INSERT INTO sales VALUES (30001,0,50)")
        now[0] = 4.999
        assert cache.get(lambda: total(c)) == 300000
        now[0] = 5
        assert cache.get(lambda: total(c)) == 300050
        assert (cache.loads, cache.hits) == (2, 2)
        return {"source_loads": cache.loads, "cache_hits": cache.hits,
                "old_before_ttl": 300000, "at_expiry": 300050, "ttl_seconds": 5}


if __name__ == "__main__":
    print(json.dumps(run()))
```

在仓库根目录或重建后的目录，执行实验模块；独立回放命令从仓库根目录执行：

```bash
uv run python -m labs.query.derived.v3
uv run python tests/query/derived/replay_q04.py --version 3
```

## 验证与边界

断言源加载次数=2、命中次数=2，4.999 时仍读旧值，5 时回源。过期不会静默返回旧值：回源抛错时错误向调用者传播，也不保存失败结果。本例没有 stale-if-error 策略。下一版加入更新后失效；单独失效仍不能防止较早开始的读取把旧数据重新填回来。

回放将本页所有 checkpoint 文件写入新的临时目录，PYTHONPATH 仅指向该目录，再启动独立解释器执行对应版本。缺少 DSN 时明确失败，不以跳过冒充成功。数据库 buffer hit/read 是 PostgreSQL 层的访问，不直接等于物理设备 I/O；EXPLAIN 的耗时为本机采样，不能替代容量测试。逻辑 TTL 时钟与数据库锁等待的墙钟测量分别命名，避免混淆。
