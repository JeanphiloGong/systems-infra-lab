# S02 v2：叶页分裂，根开始指路

前置 [v1](../v1/tutorial.md)。容量为 3 的叶中已有 10、20、30，再插入 40 被拒绝。我们要保留全部四条，同时让每页容量仍不超过 3。本版只允许两层树：一个内部根和若干叶。内部根满后的递归分裂留给下一篇。

## 1. 把溢出的一页变成两页

先把新记录按顺序插入，四条按中点分成 [10,20] 和 [30,40]。父节点的分隔键使用右页最小键 30，30 的值仍留在右叶；这体现 B+Tree 的值在叶中的选择。

内部节点保存 keys 与 children，两者长度关系为 children = keys + 1。分隔键 30 表示左边小于 30，右边大于等于 30，因此内部定位用 bisect_right；叶中找相等位置仍用 bisect_left。若两处都用 bisect_left，查 30 就会误入左叶返回 None。

页对象使用 dataclass 简化字段声明，eq=False 让页身份按对象区别，避免两个内容相同的页被当成同页。Leaf 保留 v1 的 items；容量由整棵树统一持有。Internal 是首次叶分裂后才需要的路由结构，内部不保存商品值。

## 2. 在根容量边界之前停下来

内部容量以子节点数计，至少为 3；叶容量至少为 2。本版每次叶分裂把新分隔键插入根，根只连接叶子。若根已有最大子节点数且这次新键会令叶溢出，就在修改任何内容之前抛出 OverflowError。已有键覆盖不需要分裂，即使容量已满仍允许。

validate 用断言验证严格有序、叶容量、子节点数、父分隔键等于右子树最小值、叶同深以及高度不超过两层。断言用于实验诊断，不能作为不可信磁盘输入校验；不要用 python -O 跑这些检查。

下面完整替换 labs/storage/bplus_tree/tree.py，不需要导入旧的 LeafPage。v1 的单叶类留作历史对照，本版给它增加父节点关系并将容量提升为树级约定。

将下面的完整代码保存为 `labs/storage/bplus_tree/tree.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/bplus_tree/tree.py -->
```python
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from typing import Generic, TypeVar

Value = TypeVar("Value")


@dataclass(eq=False)
class Leaf(Generic[Value]):
    items: list[tuple[int, Value]] = field(default_factory=list)


@dataclass(eq=False)
class Internal(Generic[Value]):
    keys: list[int] = field(default_factory=list)
    children: list[Leaf[Value] | Internal[Value]] = field(default_factory=list)


class BPlusTree(Generic[Value]):
    def __init__(self, leaf_capacity: int = 4, internal_capacity: int = 4) -> None:
        if leaf_capacity < 2 or internal_capacity < 3:
            raise ValueError("leaf capacity >= 2 and internal capacity >= 3 required")
        self.leaf_capacity = leaf_capacity
        self.internal_capacity = internal_capacity
        self.root: Leaf[Value] | Internal[Value] = Leaf()
        self.height = 1

    def _leaf(self, key: int) -> Leaf[Value]:
        node = self.root
        while isinstance(node, Internal):
            node = node.children[bisect_right(node.keys, key)]
        return node

    def get(self, key: int) -> Value | None:
        leaf = self._leaf(key)
        position = bisect_left([item[0] for item in leaf.items], key)
        if position < len(leaf.items) and leaf.items[position][0] == key:
            return leaf.items[position][1]
        return None

    def insert(self, key: int, value: Value) -> None:
        leaf = self._leaf(key)
        position = bisect_left([item[0] for item in leaf.items], key)
        if position < len(leaf.items) and leaf.items[position][0] == key:
            leaf.items[position] = (key, value)
            return
        if (len(leaf.items) == self.leaf_capacity
                and isinstance(self.root, Internal)
                and len(self.root.children) == self.internal_capacity):
            raise OverflowError("internal split belongs to v3")
        leaf.items.insert(position, (key, value))
        if len(leaf.items) <= self.leaf_capacity:
            return
        middle = len(leaf.items) // 2
        right = Leaf(leaf.items[middle:])
        leaf.items = leaf.items[:middle]
        separator = right.items[0][0]
        if isinstance(self.root, Leaf):
            self.root = Internal([separator], [leaf, right])
            self.height = 2
        else:
            index = self.root.children.index(leaf)
            self.root.keys.insert(index, separator)
            self.root.children.insert(index + 1, right)

    def validate(self) -> bool:
        leaves: list[Leaf[Value]] = []
        depths: set[int] = set()

        def walk(node: Leaf[Value] | Internal[Value], depth: int) -> list[int]:
            if isinstance(node, Leaf):
                keys = [key for key, _ in node.items]
                assert keys == sorted(set(keys))
                assert len(keys) <= self.leaf_capacity
                if node is not self.root:
                    assert len(keys) >= (self.leaf_capacity + 1) // 2
                leaves.append(node)
                depths.add(depth)
                return keys
            assert len(node.children) == len(node.keys) + 1
            minimum = 2 if node is self.root else (self.internal_capacity + 1) // 2
            assert minimum <= len(node.children) <= self.internal_capacity
            ranges = [walk(child, depth + 1) for child in node.children]
            assert all(part for part in ranges)
            assert all(ranges[i][-1] < ranges[i + 1][0] for i in range(len(ranges) - 1))
            assert node.keys == [part[0] for part in ranges[1:]]
            return [key for part in ranges for key in part]

        assert self.height <= 2
        walk(self.root, 1)
        assert depths == {self.height}
        return True
```

在仓库根目录运行这个检查，不依赖当前最终版本的测试文件：

```bash
uv run python - <<'PY'
from labs.storage.bplus_tree.tree import BPlusTree, Internal

tree = BPlusTree[str](3, 3)
for key in (10, 20, 30, 40):
    tree.insert(key, str(key))
assert isinstance(tree.root, Internal)
assert tree.root.keys == [30]
assert tree.get(30) == "30"
for key in (50, 60, 70):
    tree.insert(key, str(key))
assert tree.validate()
before = [tree.get(key) for key in range(10, 81, 10)]
try:
    tree.insert(80, "80")
except OverflowError:
    pass
else:
    raise AssertionError("internal overflow was silently accepted")
assert [tree.get(key) for key in range(10, 81, 10)] == before
tree.insert(70, "updated")
assert tree.get(70) == "updated"
assert tree.validate()
print("v2 leaf splits and bounded root ok")
PY
```

预期输出最后一行的 v2 成功信息。检查直接针对本版的新增能力；完整旧版可通过 replay_s02.py 从正文抽取后隔离执行。本版本只保证内存中的结构，不声称崩溃恢复。
