# S02 v3：让分裂沿插入路径向上传播

前置 [v2](../v2/tutorial.md)。容量 3 的根已有三个叶子，继续插入 80 会遇到 internal split belongs to v3。叶分裂本身已经正确，缺少的是父节点也可能溢出的处理。

## 1. 让一次插入返回它的结构变化

上一版直接把叶分裂插入唯一根，多一层后就不能假设叶的父亲是根。改成递归 _insert(node,key,value)：没有分裂返回 None；发生分裂返回 (分隔键,新右节点)。调用栈天然知道父节点，避免为了每次分裂遍历整棵树寻找父亲。

叶分裂仍复制右叶最小键给父亲，键值保留在叶。内部节点接到子节点返回后，在原来的子节点位置右侧插入 sibling。没有溢出就停止向上传播；否则继续返回自己的分裂。

## 2. 内部分裂的中间键需要提升

以内部 keys=[30,50,70]、children=[A,B,C,D] 为例，提升 50，左边保留 keys=[30] 和 [A,B]，右边保留 keys=[70] 和 [C,D]。50 从内部节点移走，成为更高父节点的分隔键。不能像叶分裂那样把它同时保留在右内部节点，否则 keys 与 children 的数量对应关系错误。

公共 insert 只处理“原根也分裂”这一种特殊情况：新建更高根，高度加一。其他位置全部由递归返回处理。validate 检查各叶深度等于 height，并验证非根最小占用：叶至少 ceil(leaf_capacity/2) 条，内部至少 ceil(internal_capacity/2) 个孩子。

下面完整替换 tree.py。相较 v2，只解除了根的溢出拒绝并加入递归传播；仍没有叶链、范围接口或磁盘。

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
        split = self._insert(self.root, key, value)
        if split is not None:
            separator, right = split
            self.root = Internal([separator], [self.root, right])
            self.height += 1

    def _insert(
        self, node: Leaf[Value] | Internal[Value], key: int, value: Value,
    ) -> tuple[int, Leaf[Value] | Internal[Value]] | None:
        if isinstance(node, Leaf):
            position = bisect_left([item[0] for item in node.items], key)
            if position < len(node.items) and node.items[position][0] == key:
                node.items[position] = (key, value)
                return None
            node.items.insert(position, (key, value))
            if len(node.items) <= self.leaf_capacity:
                return None
            middle = len(node.items) // 2
            right = Leaf(node.items[middle:])
            node.items = node.items[:middle]
            return right.items[0][0], right
        position = bisect_right(node.keys, key)
        split = self._insert(node.children[position], key, value)
        if split is None:
            return None
        separator, sibling = split
        node.keys.insert(position, separator)
        node.children.insert(position + 1, sibling)
        if len(node.children) <= self.internal_capacity:
            return None
        middle = len(node.keys) // 2
        promoted = node.keys[middle]
        right_internal = Internal(node.keys[middle + 1:], node.children[middle + 1:])
        node.keys = node.keys[:middle]
        node.children = node.children[:middle + 1]
        return promoted, right_internal

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

        walk(self.root, 1)
        assert depths == {self.height}
        return True
```

在仓库根目录运行这个检查，不依赖当前最终版本的测试文件：

```bash
uv run python - <<'PY'
import random
from labs.storage.bplus_tree.tree import BPlusTree

for capacity in (3, 4, 5):
    tree = BPlusTree[int](capacity, capacity)
    keys = list(range(100))
    random.Random(7).shuffle(keys)
    reference = {}
    for key in keys:
        tree.insert(key, key * 10)
        reference[key] = key * 10
        assert tree.validate()
        assert all(tree.get(k) == v for k, v in reference.items())
    assert tree.height >= 3
    tree.insert(30, -30)
    assert tree.get(30) == -30 and tree.validate()
    assert tree.get(100) is None
print("v3 recursive splits ok")
PY
```

预期输出最后一行的 v3 成功信息。检查直接针对本版的新增能力；完整旧版可通过 replay_s02.py 从正文抽取后隔离执行。本版本只保证内存中的结构，不声称崩溃恢复。
