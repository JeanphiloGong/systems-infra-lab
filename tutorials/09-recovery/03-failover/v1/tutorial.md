# A03 v1：High Availability 与 Failover

v0 只看到中断；现在操作者停止旧主、提升 b，再把客户端写入目标改为 b。模型中的 stop 在 promote 之前，保护的是旧主不能继续接受写入；promote 本身并不是完整的故障隔离方案。比较故障前已确认订单与 b 的内容，再确认写入 two 成功，分别验证数据保留和服务恢复。

真实 PostgreSQL probe 位于 labs/recovery/ha/postgres_probe.py：它先写 primary，等待 standby 的 replay LSN 越过确认位置，然后 pg_promote，最后直接连接 standby 写入。它返回 old_primary_fence_required=true，说明程序没有执行 fencing，也没有更新应用的连接路由。手动实验期间不得向旧主发业务请求；模块 README 的停止旧 primary 命令是操作者负责的后续隔离，存在双主窗口，不能作为安全生产切换顺序。完整生产演练需在允许新主业务写入前隔离旧主并切换连接入口。

本版模型不测真实 promotion 耗时；真实 probe 也未自动验证所有旧客户端退出。下一版用 Patroni 接管领导锁与检测，仍需解释误判。

模型重放：`uv run python tests/recovery/ha/replay_a03.py`。

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

