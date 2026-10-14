# S02 v6：删除先保证结果和根收缩

前置 v5。删除最后一个键时，根不应留下空的内部节点。本版在叶页欠载时从左/右兄弟借一条记录，无法借出时合并叶页并更新父分隔键；父内部节点也沿同一规则借位或合并，根只保留一个子节点时收缩。它仍不处理并发删除或持久化写回。

本版本的最终 checkpoint 包含完整的 `tree.py`，包括 v4 的插入/扫描、叶页借位与合并、内部节点借位与合并、祖先分隔键刷新和根收缩；读者不需要从 v4 拼接片段。

本版将完整实现直接冻结如下，读者可以保存为目标文件后运行，不需要由 replay harness 补文件。

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

    def _find_parent(self, node: Leaf[Value] | Internal[Value], child: Leaf[Value] | Internal[Value]) -> Internal[Value] | None:
        if not isinstance(node, Internal):
            return None
        if any(candidate is child for candidate in node.children):
            return node
        for candidate in node.children:
            parent = self._find_parent(candidate, child)
            if parent is not None:
                return parent
        return None

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

    def delete(self, key: int) -> bool:
        deleted, _ = self._delete(self.root, key, is_root=True)
        while isinstance(self.root, Internal) and len(self.root.children) == 1:
            self.root = self.root.children[0]
            self.height -= 1
        return deleted

    def _delete(
        self,
        node: Leaf[Value] | Internal[Value],
        key: int,
        *,
        is_root: bool,
    ) -> tuple[bool, bool]:
        """Delete one key and return (deleted, underflow)."""
        if isinstance(node, Leaf):
            position = bisect_left([item[0] for item in node.items], key)
            if position == len(node.items) or node.items[position][0] != key:
                return False, False
            node.items.pop(position)
            minimum = (self.leaf_capacity + 1) // 2
            return True, not is_root and len(node.items) < minimum

        index = bisect_right(node.keys, key)
        child = node.children[index]
        deleted, underflow = self._delete(child, key, is_root=False)
        if not deleted:
            return False, False
        if underflow:
            self._rebalance_child(node, index)
        self._refresh_keys(node)
        minimum = (self.internal_capacity + 1) // 2
        return True, not is_root and len(node.children) < minimum

    def _rebalance_child(self, parent: Internal[Value], index: int) -> None:
        child = parent.children[index]
        left = parent.children[index - 1] if index else None
        right = parent.children[index + 1] if index + 1 < len(parent.children) else None
        minimum_leaf = (self.leaf_capacity + 1) // 2
        minimum_internal = (self.internal_capacity + 1) // 2

        if isinstance(child, Leaf):
            if isinstance(left, Leaf) and len(left.items) > minimum_leaf:
                child.items.insert(0, left.items.pop())
                return
            if isinstance(right, Leaf) and len(right.items) > minimum_leaf:
                child.items.append(right.items.pop(0))
                return
            if isinstance(left, Leaf):
                left.items.extend(child.items)
                left.next = child.next
                parent.children.pop(index)
            elif isinstance(right, Leaf):
                child.items.extend(right.items)
                child.next = right.next
                parent.children.pop(index + 1)
            return

        if isinstance(left, Internal) and len(left.children) > minimum_internal:
            child.children.insert(0, left.children.pop())
            self._refresh_keys(left)
            self._refresh_keys(child)
            return
        if isinstance(right, Internal) and len(right.children) > minimum_internal:
            child.children.append(right.children.pop(0))
            self._refresh_keys(right)
            self._refresh_keys(child)
            return
        if isinstance(left, Internal):
            left.children.extend(child.children)
            self._refresh_keys(left)
            parent.children.pop(index)
        elif isinstance(right, Internal):
            child.children.extend(right.children)
            self._refresh_keys(child)
            parent.children.pop(index + 1)

    def _refresh_keys(self, node: Internal[Value]) -> None:
        def first_key(child: Leaf[Value] | Internal[Value]) -> int:
            while isinstance(child, Internal):
                child = child.children[0]
            if not child.items:
                raise ValueError("empty leaf in tree")
            return child.items[0][0]
        node.keys = [first_key(child) for child in node.children[1:]]

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

运行：

```bash
uv run pytest tests/storage/bplus_tree/test_s02_delete.py -q
```

```bash
uv run python - <<'PY'
from labs.storage.bplus_tree.tree import BPlusTree

tree = BPlusTree[int](3, 3)
for key in range(12):
    tree.insert(key, key)
for key in range(12):
    assert tree.delete(key)
    assert tree.validate()
assert tree.height == 1
print("v6 delete rebalance ok")
PY
```

检查逐个删除 12 个键、根收缩到高度 1、叶借位/合并、内部借位/合并和删除缺失键无副作用。删除不触及 v5 页文件；持久化删除写回和崩溃原子性不在本版。
