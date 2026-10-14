# S02 v5：把页号和根元数据写进固定页

前置 v4。保存全部键值后再逐项插回会丢失页拓扑，也不能验证页损坏。这里定义固定 256 字节页：第 0 页是元页，之后是节点页；每页尾部保存 CRC32。叶页保存 `(key,value)` 与 next 页号，内部页保存 child page IDs 和分隔键。打开时按页号连接对象，绝不重新插入键。

本版只保证完整写入文件的编码和读取；`path.open("wb")` 中途退出可能留下截断文件。WAL 与崩溃恢复仍属于 S03，不能从本版 `save` 推导出来。

完整实现位于 `labs/storage/bplus_tree/page_file.py`，包含固定页编码、元页、节点页、CRC 校验、拓扑重建和 signed-64-bit 键值边界。以下是本版本完整检查点：

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

<!-- checkpoint: labs/storage/bplus_tree/page_file.py -->
```python
from pathlib import Path
from struct import Struct
import zlib

from labs.storage.bplus_tree.tree import BPlusTree, Internal, Leaf

PAGE_SIZE = 256
META = Struct("<8s6I")
HEAD = Struct("<BII")
PAIR = Struct("<qq")
KEY = Struct("<q")
ID = Struct("<I")
MAGIC = b"BPLUS001"


def checked_page(body: bytes) -> bytes:
    if len(body) > PAGE_SIZE - ID.size:
        raise ValueError("page capacity exceeds encoded page size")
    padded = body.ljust(PAGE_SIZE - ID.size, b"\0")
    return padded + ID.pack(zlib.crc32(padded))


def save(tree: BPlusTree[int], path: Path) -> None:
    tree.validate()
    nodes = [tree.root]
    for node in nodes:
        if isinstance(node, Internal):
            nodes.extend(node.children)
    ids = {id(node): index + 1 for index, node in enumerate(nodes)}
    pages = [checked_page(META.pack(MAGIC, 1, tree.leaf_capacity, tree.internal_capacity, ids[id(tree.root)], len(nodes), tree.height))]
    for node in nodes:
        if isinstance(node, Leaf):
            body = HEAD.pack(1, len(node.items), ids[id(node.next)] if node.next else 0)
            for key, value in node.items:
                if any(type(number) is not int or not -(2**63) <= number < 2**63 for number in (key, value)):
                    raise ValueError("page codec requires signed 64-bit integer keys and values")
                body += PAIR.pack(key, value)
        else:
            body = HEAD.pack(2, len(node.children), 0)
            body += b"".join(ID.pack(ids[id(child)]) for child in node.children)
            body += b"".join(KEY.pack(key) for key in node.keys)
        pages.append(checked_page(body))
    with path.open("wb") as target:
        for page in pages:
            target.write(page)


def load(path: Path) -> BPlusTree[int]:
    data = path.read_bytes()
    if not data or len(data) % PAGE_SIZE:
        raise ValueError("truncated page file")
    pages = [data[offset:offset + PAGE_SIZE] for offset in range(0, len(data), PAGE_SIZE)]
    for page in pages:
        if zlib.crc32(page[:-ID.size]) != ID.unpack_from(page, PAGE_SIZE - ID.size)[0]:
            raise ValueError("page checksum mismatch")
    magic, version, leaf_cap, internal_cap, root_id, count, height = META.unpack_from(pages[0])
    if magic != MAGIC or version != 1 or count != len(pages) - 1 or not 1 <= root_id <= count:
        raise ValueError("invalid root metadata")
    tree = BPlusTree[int](leaf_cap, internal_cap)
    nodes = {}
    links = {}
    next_ids = {}
    for page_id, page in enumerate(pages[1:], 1):
        kind, size, next_id = HEAD.unpack_from(page)
        if kind == 1:
            nodes[page_id] = Leaf([PAIR.unpack_from(page, HEAD.size + i * PAIR.size) for i in range(size)])
            next_ids[page_id] = next_id
        elif kind == 2:
            children = [ID.unpack_from(page, HEAD.size + i * ID.size)[0] for i in range(size)]
            nodes[page_id] = Internal([KEY.unpack_from(page, HEAD.size + size * ID.size + i * KEY.size)[0] for i in range(size - 1)])
            links[page_id] = children
        else:
            raise ValueError("invalid page header")
    seen = set()
    def connect(page_id):
        if page_id not in nodes or page_id in seen:
            raise ValueError("invalid or repeated child page")
        seen.add(page_id)
        node = nodes[page_id]
        if isinstance(node, Internal):
            node.children = [connect(child) for child in links[page_id]]
        return node
    tree.root = connect(root_id)
    if len(seen) != count:
        raise ValueError("unreachable page")
    for page_id, next_id in next_ids.items():
        if next_id:
            nodes[page_id].next = nodes[next_id]
    tree.height = height
    tree.validate()
    return tree

```bash
uv run pytest tests/storage/bplus_tree/test_s02_persist.py -q
```

检查覆盖 100 个随机插入后的页拓扑重开、空树、负键值、截断、额外字节、CRC 损坏和不可编码值不覆盖旧文件。通过后，持久化的是页结构与根页元数据，而不是一个会重新插入的键值清单；下一篇才处理删除借位、合并与根收缩。

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.bplus_tree.page_file import load, save
from labs.storage.bplus_tree.tree import BPlusTree

with TemporaryDirectory() as directory:
    path = Path(directory) / "tree.pages"
    tree = BPlusTree[int](3, 3)
    for key in range(20):
        tree.insert(key, key * 10)
    save(tree, path)
    reopened = load(path)
    assert reopened.scan(0, 19) == [(key, key * 10) for key in range(20)]
print("v5 page checkpoint ok")
PY
```
