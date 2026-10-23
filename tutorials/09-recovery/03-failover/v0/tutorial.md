# A03 v0：High Availability 与 Failover

本版先定义失败，而不是先许诺自动恢复。订单写入 a 得到确认后，停止 a，再推进逻辑时钟 3 个单位；此时记录 rto_window 与 b 上的数据。这里的 3 是观察结束时间，不是恢复完成时间，因此只能说中断至少持续此窗口，不能报告 RTO=3 秒。模型 write 同步复制，b 含订单不能证明真实异步数据库的 RPO。

RTO 的实测起点应是故障注入，终点是客户端再次成功提交；RPO 要比较故障前已确认记录集合与恢复后记录集合。没有恢复就没有完整 RTO 测量。单实例没有可写服务时，即使磁盘数据还在，客户端仍不可用。下面完整模型提前包含后续机制，仅为独立重放提供依赖；本版只解释 experiment.py 的 version==0 分支，不把其余方法称为本版新增实现。运行仓库重放器可验证逻辑轨迹，真实时间留给 v2。

下一版由人决定提升副本，解决可写服务恢复，但还需要交代旧主隔离和客户端目标。

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

运行：`python experiment.py 0`。RTO/RPO 是本次轨迹的观测值，不是年度可用性承诺；真实 PostgreSQL promotion 需要独立容器实验。

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/recovery/ha/replay_a03.py
```

</details>
