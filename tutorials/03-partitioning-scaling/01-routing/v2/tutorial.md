# P01 v2：范围查询为什么要保留键的顺序

[v1](../v1/tutorial.md) 的哈希路由对点查很方便。但要查询 `[99,101)` 的全部订单，
一般无法从两个端点知道中间键属于哪些哈希分片，往往需要散发查询后合并结果。
现在尝试另一种布局：a 保存 ID<100，b 保存 100≤ID<200，c 保存 ID≥200。

这是一种替代策略实验，不替换前一篇文件，也不建立通用路由框架。
输入仍为整数 ID；如果实际业务按时间或字符串分区，需要重新定义比较与边界语义。

## 1. 让边界有唯一归属

ID 恰好等于 100 时放到 b，而不是同时放入 a 和 b。Python 的 `bisect_right`
返回它应插到所有相等分界右侧的位置，因此适合这个约定：

```python
from bisect import bisect_right

cuts = (100, 200)
assert bisect_right(cuts, 99) == 0
assert bisect_right(cuts, 100) == 1
assert bisect_right(cuts, 200) == 2
```

两个分界产生三个区间，首尾分别延伸到整数域两端。本模型接受负整数 ID；
实际业务是否允许负 ID 应由外部入口决定，不影响这里的路由推导。
重复或乱序分界让区间定义含混，因此配置必须严格递增。

## 2. 查询哪些区间可能包含结果

对于非空整数范围 `[start,stop)`，最小可能键是 start，最大可能键是 stop-1。
分别找到两者的区间，就得到需要访问的连续节点切片。空范围不用访问任何节点。

在上一段示例末尾添加这个局部 patch：

```python
nodes = ("a", "b", "c")
first = bisect_right(cuts, 99)
last = bisect_right(cuts, 101 - 1)
assert nodes[first:last + 1] == ("a", "b")
```

这只裁剪可能有结果的节点，节点内部仍需应用 `start <= key < stop` 过滤。
把整个 b 分片全返回会带回 101 到 199 的多余订单。`stop-1` 的写法依赖整数域，
不能原样用于字符串、浮点或其他没有这种前驱定义的键。

## 3. 完整检查点与递增键的代价

点查和范围查询都要使用同一配置，于是用 `RangeMap` 保存两个元组。
它不管理数据库、自动迁移或缓存。新建 `labs/partitioning/routing/ranges.py`：

<!-- checkpoint: labs/partitioning/routing/ranges.py -->
```python
from bisect import bisect_right


class RangeMap:
    def __init__(self, cuts: tuple[int, ...], nodes: tuple[str, ...]) -> None:
        if len(nodes) != len(cuts) + 1 or len(set(nodes)) != len(nodes):
            raise ValueError("one unique node is required per range")
        if any(left >= right for left, right in zip(cuts, cuts[1:])):
            raise ValueError("cuts must be strictly increasing")
        self.cuts = cuts
        self.nodes = nodes

    def node(self, order_id: int) -> str:
        return self.nodes[bisect_right(self.cuts, order_id)]

    def covering(self, start: int, stop: int) -> tuple[str, ...]:
        if start >= stop:
            return ()
        first = bisect_right(self.cuts, start)
        last = bisect_right(self.cuts, stop - 1)
        return self.nodes[first:last + 1]
```

运行下面的完整检查，既验证裁剪不丢数据，也显示一种热点：

```bash
uv run python - <<'PY'
from collections import Counter
from labs.partitioning.routing.ranges import RangeMap

route = RangeMap((100, 200), ("a", "b", "c"))
stores: dict[str, dict[int, str]] = {node: {} for node in route.nodes}
for key in range(300):
    stores[route.node(key)][key] = "paid"
assert route.node(99) == "a"
assert route.node(100) == "b"
assert route.node(200) == "c"
assert route.covering(99, 101) == ("a", "b")
assert route.covering(100, 200) == ("b",)
assert route.covering(100, 100) == ()
rows = sorted((key, value) for node in route.covering(99, 101)
              for key, value in stores[node].items() if 99 <= key < 101)
assert rows == [(99, "paid"), (100, "paid")]
traffic = Counter(route.node(key) for key in range(300, 1300))
assert traffic == {"c": 1000}
for cuts, nodes in [((100, 100), ("a", "b", "c")), ((200, 100), ("a", "b", "c")), ((100,), ("a",))]:
    try:
        RangeMap(cuts, nodes)
    except ValueError:
        pass
    else:
        raise AssertionError("bad range configuration accepted")
print("range pruning ok; all 1000 new increasing IDs route to c")
PY
```

原有 300 条订单恰好均分，并不意味着未来写入均分：递增 ID 的新订单全部进入 c。
这解释了范围裁剪与写热点的权衡。真正拆分热区间还要迁移数据与切换路由，留给 P03。
下一版回到哈希策略，减少节点增减时受影响的键，同时承认单个热键仍只有一个主要归属。
