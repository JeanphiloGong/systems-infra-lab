# P01 v3：扩容时，只让一部分键换主人

回看 [v1](../v1/tutorial.md)：1000 个固定键从三个节点扩成四个，简单取模会改变大量归属。
如果每次扩容都搬迁大半数据，网络和磁盘会长时间忙于迁移。本篇保留稳定哈希，改变“如何选节点”。
我们只计算归属，不执行迁移；已有订单不会因为算法改变而自动到达新节点。

## 1. 固定位置，而不是改变除数

把节点放在一个有序的哈希环上。键从自己的位置顺时针找到第一个节点；
超过最后一个位置，就回绕到第一个。先用三个手工位置理解这个行为：

```python
from bisect import bisect_left

points = (10, 40, 80)
owners = ("a", "b", "c")
assert owners[bisect_left(points, 40) % len(points)] == "b"
assert owners[bisect_left(points, 90) % len(points)] == "a"
```

这里恰好等于节点位置时归该节点，因此选 `bisect_left`，与前一篇范围分界的 `bisect_right` 不同。
如果在 20 增加 d，只会从 b 接走原先落在 `(10,20]` 的键；a、c 的其他区间不需要改变。
这就是减少迁移的来源：现有节点位置保持不变，不再重新计算全局除数。

## 2. 一个物理节点为什么需要多个位置

真实位置可以由节点名哈希得到，但三个随机位置对应的区间可能长短差很多。
于是每个物理节点生成多个虚拟点：对 `[节点名, 编号]` 做稳定哈希。虚拟点仍映射回同一个物理节点，
并不意味着复制多份数据。比较 1 个和 64 个虚拟点能观察分布差异，但不保证任意小样本都更均衡。

用 JSON 编码二元组，是为了让节点名包含标点时仍有无歧义的输入；固定编码参数属于协议。
增加一个新物理节点时，旧节点名和虚拟点数必须保持不变。改变旧节点的虚拟点数也会改变归属。
64 位点位碰撞虽然很少，本教学实现仍明确拒绝，避免把相同点位的拥有者选择藏在排序细节里。

## 3. 完整环与扩容检查点

保留 v1 的稳定哈希文件。为了让本检查点可独立重建，两个文件完整给出。
`HashRing` 保存排序后的点位及拥有者；`owner_at` 只查位置，`node` 先对订单 ID 哈希再调用它。
没有后台任务或存储修改。

<!-- checkpoint: labs/partitioning/routing/hashing.py -->
```python
from hashlib import sha256


def stable_hash(text: str) -> int:
    return int.from_bytes(sha256(text.encode("utf-8")).digest()[:8], "big")


def modulo_node(order_id: int, nodes: tuple[str, ...]) -> str:
    if not nodes or len(set(nodes)) != len(nodes):
        raise ValueError("nodes must be nonempty and unique")
    return nodes[stable_hash(str(order_id)) % len(nodes)]
```

新建 `labs/partitioning/routing/ring.py`，完整 checkpoint：

<!-- checkpoint: labs/partitioning/routing/ring.py -->
```python
import json
from bisect import bisect_left

from labs.partitioning.routing.hashing import stable_hash


class HashRing:
    def __init__(self, nodes: tuple[str, ...], virtual_nodes: int = 64) -> None:
        if not nodes or len(set(nodes)) != len(nodes) or virtual_nodes < 1:
            raise ValueError("unique nodes and positive virtual_nodes required")
        entries = sorted(
            (stable_hash(json.dumps([node, index], separators=(",", ":"))), node)
            for node in nodes
            for index in range(virtual_nodes)
        )
        self.points = tuple(point for point, _ in entries)
        self.owners = tuple(node for _, node in entries)
        if len(set(self.points)) != len(self.points):
            raise ValueError("ring point collision; change node configuration")

    def owner_at(self, position: int) -> str:
        index = bisect_left(self.points, position) % len(self.points)
        return self.owners[index]

    def node(self, order_id: int) -> str:
        return self.owner_at(stable_hash(str(order_id)))
```

在根目录运行以下实验。查询范围固定为 0 到 9999；输出的是这些键的归属数量，而非机器负载：

```bash
uv run python - <<'PY'
from collections import Counter
from labs.partitioning.routing.hashing import modulo_node
from labs.partitioning.routing.ring import HashRing

nodes = ("a", "b", "c")
expanded = (*nodes, "d")
old = HashRing(nodes, 64)
new = HashRing(expanded, 64)
reordered = HashRing(("c", "a", "b"), 64)
assert all(old.node(key) == reordered.node(key) for key in range(10000))
moved = [key for key in range(10000) if old.node(key) != new.node(key)]
assert moved and all(new.node(key) == "d" for key in moved)
removed = HashRing(("a", "c"), 64)
assert all(old.node(key) == "b" for key in range(10000)
           if old.node(key) != removed.node(key))
assert old.owner_at(old.points[0]) == old.owners[0]
assert old.owner_at(old.points[-1] + 1) == old.owners[0]
modulo_moved = sum(modulo_node(key, nodes) != modulo_node(key, expanded) for key in range(10000))
print(f"ring moved={len(moved)}/10000; modulo moved={modulo_moved}/10000")
for count in (1, 64):
    ring = HashRing(nodes, count)
    print(f"virtual_nodes={count}: {dict(sorted(Counter(ring.node(key) for key in range(10000)).items()))}")
for configuration, count in [((), 1), (("a", "a"), 1), (("a",), 0)]:
    try:
        HashRing(configuration, count)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid ring accepted")
PY
```

新增节点后，移动的键全部进入 d；现有节点之间无需互搬这些键。移除 b 后，只有 b 原来的键改变归属。
这个性质比一次“移动比例更小”的数字更关键：它由固定旧点位和顺时针归属规则支撑。

## 4. 选择路由之后，还缺什么

| 布局 | 点查与范围查询 | 扩展时的限制 |
| --- | --- | --- |
| 单分片 | 直接点查，范围扫描全部数据 | 单节点容量与吞吐上限 |
| 简单哈希取模 | 点查单节点，范围通常散发 | 节点数变化会大量重映射 |
| 范围分区 | 点查与范围裁剪明确 | 递增键或大租户可能造成热分区 |
| 一致性哈希环 | 点查单节点，范围通常散发 | 仍需真实数据迁移与路由版本协调 |

一致性哈希不会拆开一个热键：同一订单被读取一百万次，仍去同一个主要节点。
分片不等于复制，也不提供跨分片事务。P02 接下来研究倾斜与热点，P03 再处理迁移期间的写入和路由切换。
