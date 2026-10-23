# A03 v1：High Availability 与 Failover

v0 只看到中断；现在操作者停止旧主、提升 b，再把客户端写入目标改为 b。模型中的 stop 在 promote 之前，保护的是旧主不能继续接受写入；promote 本身并不是完整的故障隔离方案。比较故障前已确认订单与 b 的内容，再确认写入 two 成功，分别验证数据保留和服务恢复。

真实实验在后面的第 2 节创建 `labs/recovery/ha/postgres_probe.py`。顺序与模型一致：先记录写入并等待副本追平，再停止旧 primary，最后提升 standby 并切换本次脚本的连接目标。停止容器是这个单机实验的隔离方式，不代表生产环境的通用 fencing。

这次主动等待追平，因此样本应保留所有已确认行；它不能证明任意异步复制故障都零丢失。下一版才交给 Patroni 负责检测和切换。

## 1. 保留 v0 模型，观察人工切换

模型重放：[参考分支检查](../../../../docs/reference-checks.md)。

将下面的完整代码保存为 `model.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: model.py -->
```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Replica:
    name: str
    role: str = "standby"
    generation: int = 0
    rows: dict[str, str] = field(default_factory=dict)
    alive: bool = True
    isolated: bool = False
    last_heartbeat: int = 0


class HACluster:
    """A two-replica failover model with explicit fencing and logical time."""

    def __init__(self) -> None:
        self.nodes = {"a": Replica("a", role="primary"), "b": Replica("b")}
        self.primary = "a"
        self.generation = 1
        self.nodes["a"].generation = self.generation
        self.now = 0
        self.events: list[dict[str, object]] = []

    def write(self, node: str, key: str, value: str) -> None:
        replica = self.nodes[node]
        if not replica.alive or replica.isolated or replica.role != "primary" or replica.generation != self.generation:
            raise RuntimeError("write fenced")
        replica.rows[key] = value
        for peer in self.nodes.values():
            if peer.name != node and peer.alive and not peer.isolated:
                peer.rows = dict(replica.rows)
                peer.generation = self.generation
        self.events.append({"at": self.now, "kind": "write", "node": node, "key": key})

    def isolate(self, node: str) -> None:
        self.nodes[node].isolated = True
        self.events.append({"at": self.now, "kind": "isolate", "node": node})

    def stop(self, node: str) -> None:
        self.nodes[node].alive = False
        self.events.append({"at": self.now, "kind": "stop", "node": node})

    def promote(self, node: str) -> None:
        candidate = self.nodes[node]
        if not candidate.alive or candidate.isolated:
            raise RuntimeError("candidate unavailable")
        old = self.primary
        self.generation += 1
        candidate.role, candidate.generation = "primary", self.generation
        self.primary = node
        self.nodes[old].role = "standby"
        self.events.append({"at": self.now, "kind": "promote", "old": old, "new": node, "generation": self.generation})

    def tick(self, seconds: int, timeout: int = 5) -> None:
        if seconds < 0:
            raise ValueError("logical time cannot go backwards")
        self.now += seconds
        current = self.nodes[self.primary]
        if current.alive and not current.isolated:
            for peer in self.nodes.values():
                if peer.name != self.primary and peer.alive and not peer.isolated:
                    peer.last_heartbeat = self.now
        if not current.alive or current.isolated:
            candidates = [node for node in self.nodes.values() if node.name != self.primary and node.alive and not node.isolated]
            if candidates and self.now - candidates[0].last_heartbeat >= timeout:
                self.promote(candidates[0].name)

    def rejoin(self, node: str) -> None:
        replica = self.nodes[node]
        if replica.alive and not replica.isolated:
            replica.rows = dict(self.nodes[self.primary].rows)
            replica.generation = self.generation
            replica.role = "standby"
            self.events.append({"at": self.now, "kind": "rejoin", "node": node, "generation": self.generation})
```

将下面的完整代码保存为 `experiment.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: experiment.py -->
```python
import json
import sys
from model import HACluster
cluster = HACluster()
version = int(sys.argv[1])
cluster.write('a', 'order', 'one')
if version == 0:
    cluster.stop('a'); cluster.tick(3); result = {'rto_window': cluster.now, 'rpo_rows': cluster.nodes['b'].rows}
elif version == 1:
    cluster.stop('a'); cluster.promote('b'); cluster.write('b', 'order', 'two'); result = {'primary': cluster.primary, 'confirmed': cluster.nodes['b'].rows}
elif version == 2:
    cluster.stop('a'); cluster.tick(6); result = {'automatic_primary': cluster.primary, 'generation': cluster.generation}
elif version == 3:
    cluster.isolate('a'); cluster.promote('b')
    try: cluster.write('a', 'order', 'stale')
    except RuntimeError: fenced = True
    else: fenced = False
    cluster.write('b', 'order', 'two'); result = {'old_primary_fenced': fenced, 'new_value': cluster.nodes['b'].rows['order']}
elif version == 4:
    cluster.stop('a'); cluster.promote('b'); cluster.write('b', 'order', 'two')
    cluster.nodes['a'].alive = True; cluster.rejoin('a'); cluster.promote('a'); cluster.write('a', 'order', 'three')
    result = {'cutover_primary': cluster.primary, 'rows': cluster.nodes['a'].rows}
else: raise ValueError('version must be 0..4')
print(json.dumps(result, sort_keys=True))
```

运行：`python experiment.py 1`。RTO/RPO 是本次轨迹的观测值，不是年度可用性承诺；真实 PostgreSQL promotion 需要独立容器实验。

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/recovery/ha/replay_a03.py
```

</details>

## 2. 在真实副本上执行相同顺序

先完成 [R04 v0](../../../05-replication/04-postgres/v0/tutorial.md) 的 Compose 与三个挂载文件。只使用该实验的 55440/55441/55442 端口；每次演练从新的 R04 实验卷开始，已经提升过的副本不能再作为原 standby 重复本流程。先在 R04 环境执行其正常清理，再重新启动。

新建 `labs/recovery/ha/postgres_probe.py`。`prepare` 写入并等待同一 WAL 位置到达 standby；`promote` 只连接 standby。把两步拆开是为了让操作者在中间完成旧主隔离，而不是在两个可写主都存在时继续写。

<!-- checkpoint: labs/recovery/ha/postgres_probe.py -->

```python
from __future__ import annotations

import argparse
import json
import time

import psycopg


def connect(port: int) -> psycopg.Connection:
    deadline = time.monotonic() + 30
    while True:
        try:
            return psycopg.connect(host="127.0.0.1", port=port, dbname="r04",
                                   user="r04", password="r04_local_only",
                                   autocommit=True, connect_timeout=2)
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.1)


def prepare() -> dict[str, object]:
    with connect(55440) as primary, connect(55441) as standby:
        assert not primary.execute("SELECT pg_is_in_recovery()").fetchone()[0]
        assert standby.execute("SELECT pg_is_in_recovery()").fetchone()[0]
        primary.execute("DROP TABLE IF EXISTS a03_probe")
        primary.execute("CREATE TABLE a03_probe (id integer PRIMARY KEY, value text NOT NULL)")
        primary.execute("INSERT INTO a03_probe VALUES (1, 'before-promotion')")
        target = primary.execute("SELECT pg_current_wal_lsn()").fetchone()[0]
        deadline = time.monotonic() + 30
        while not standby.execute("SELECT pg_last_wal_replay_lsn() >= %s::pg_lsn", (target,)).fetchone()[0]:
            if time.monotonic() >= deadline:
                raise TimeoutError("standby did not catch up")
            time.sleep(0.1)
        assert standby.execute("SELECT * FROM a03_probe ORDER BY id").fetchall() == [(1, "before-promotion")]
        return {"ready_to_stop_primary": True, "replayed_lsn": str(target)}


def promote() -> dict[str, object]:
    # The documented stop-primary command must complete before this call.
    with connect(55441) as standby:
        assert standby.execute("SELECT pg_is_in_recovery()").fetchone()[0]
        assert standby.execute("SELECT pg_promote(wait => true, wait_seconds => 30)").fetchone()[0]
        assert not standby.execute("SELECT pg_is_in_recovery()").fetchone()[0]
        standby.execute("INSERT INTO a03_probe VALUES (2, 'after-promotion')")
        rows = standby.execute("SELECT * FROM a03_probe ORDER BY id").fetchall()
        assert rows == [(1, "before-promotion"), (2, "after-promotion")]
        return {"replica_promoted": True, "confirmed_rows_preserved": True, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "promote"])
    args = parser.parse_args()
    print(json.dumps(prepare() if args.action == "prepare" else promote()))
```

## 3. 检查保留记录和新的写入口

从仓库根目录依次执行。`prepare` 输出 ready_to_stop_primary=true 后，停止命令必须成功，再执行 promote：

```bash
docker compose -f infra/r04.compose.yaml up -d --wait
uv run python -m labs.recovery.ha.postgres_probe prepare
docker compose -f infra/r04.compose.yaml stop primary
uv run python -m labs.recovery.ha.postgres_probe promote
```

最终 `rows` 同时包含 before-promotion 与 after-promotion；`confirmed_rows_preserved=true` 来自实际查询。连接重试只为等待容器初始化，不重试业务 INSERT，因此不会把重复副作用藏在工具函数里。

本版手动更新了脚本连接的端口，没有实现应用连接池重连、DNS/VIP 切换或自动旧主回归。完成后清理此专用栈，下一版 Patroni 使用另一套环境：

```bash
docker compose -f infra/r04.compose.yaml down -v
```
