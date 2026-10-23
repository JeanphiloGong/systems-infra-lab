# S02 v4：一次下降，沿叶子完成闭区间扫描

前置 [v3](../v3/tutorial.md)。现在可以查询任意主键，但页面请求 [17,24] 若逐个 get，需要重复走根到叶的路径；而真实键可能稀疏，不能枚举所有整数。我们需要从第一片叶开始，按已有记录访问下一叶。

## 1. 分裂时维护叶链

新增 Leaf.next 指向右侧相邻叶。原叶 A 分成 A、B，原来的后继 C 不能丢失：先让 B.next=A.next，再令 A.next=B。内部节点不需要链，B+Tree 的全量值在叶中。链接只在叶分裂处修改，因此重复键覆盖不影响它。

## 2. 明确范围边界

scan(start,end) 使用闭区间，包含相等端点。start>end 返回空；get 不变。先用 _leaf(start) 下降一次，在该页跳过较小键，随后顺着 next 读取；遇到 key>end 立刻结束。全树无记录时空根叶也自然返回空。

validate 在原结构检查之后，比较树的深度优先叶序与 next 链，最后叶 next 必须为 None。这能发现漏接、接错以及尾部环回。它是诊断代码，会遍历整棵树，不计入正常点查成本。

下面完整替换 tree.py，只新增 next、分裂链接、scan 与链检查。尚未写磁盘，下一篇会先定义页号和二进制页边界，而不是把整个键集合保存后重新插入。

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
    next: Leaf[Value] | None = None


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
            right = Leaf(node.items[middle:], node.next)
            node.items = node.items[:middle]
            node.next = right
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

    def scan(self, start: int, end: int) -> list[tuple[int, Value]]:
        if start > end:
            return []
        leaf: Leaf[Value] | None = self._leaf(start)
        result: list[tuple[int, Value]] = []
        while leaf is not None:
            for key, value in leaf.items:
                if key > end:
                    return result
                if key >= start:
                    result.append((key, value))
            leaf = leaf.next
        return result

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
        assert all(leaves[i].next is leaves[i + 1] for i in range(len(leaves) - 1))
        assert leaves[-1].next is None
        return True
```

在仓库根目录运行这个检查，不依赖当前最终版本的测试文件：

```bash
uv run python - <<'PY'
import random
from labs.storage.bplus_tree.tree import BPlusTree

tree = BPlusTree[int](3, 3)
keys = list(range(100))
random.Random(7).shuffle(keys)
for key in keys:
    tree.insert(key, key * 10)
assert tree.validate()
assert tree.scan(17, 24) == [(key, key * 10) for key in range(17, 25)]
assert tree.scan(30, 30) == [(30, 300)]
assert tree.scan(40, 30) == []
assert tree.scan(100, 200) == []
assert tree.scan(-10, 2) == [(0, 0), (1, 10), (2, 20)]
assert tree.scan(-10, 200) == [(key, key * 10) for key in range(100)]
print("v4 leaf chain inclusive ranges ok")
PY
```

预期输出最后一行的 v4 成功信息。检查直接针对本版的新增能力；完整旧版可通过 replay_s02.py 从正文抽取后隔离执行。本版本只保证内存中的结构，不声称崩溃恢复。
