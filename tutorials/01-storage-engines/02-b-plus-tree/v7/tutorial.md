# S02 v7：完整检查点与边界

最终 checkpoint 必须组装 v6 修正后的完整 tree.py 与 v5 page_file.py，并保留数组参考。能力包括点查、闭区间扫描、页拓扑重开、局部删除重平衡和根收缩。`page_file.py` 的写入不是 WAL；进程在 `save` 中退出可能留下截断文件，CRC 和长度检查会拒绝它。

最终 checkpoint 包含下面两份完整文件，保存后即可独立运行。

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

将下面的完整代码保存为 `labs/storage/bplus_tree/page_file.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/bplus_tree/page_file.py -->
```python
from __future__ import annotations

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
    if HEAD.size + tree.leaf_capacity * PAIR.size > PAGE_SIZE - ID.size:
        raise ValueError("leaf capacity exceeds encoded page size")
    if HEAD.size + tree.internal_capacity * ID.size + (tree.internal_capacity - 1) * KEY.size > PAGE_SIZE - ID.size:
        raise ValueError("internal capacity exceeds encoded page size")
    nodes: list[Leaf[int] | Internal[int]] = [tree.root]
    for node in nodes:
        if isinstance(node, Internal):
            nodes.extend(node.children)
    ids = {id(node): index + 1 for index, node in enumerate(nodes)}
    pages = [checked_page(META.pack(
        MAGIC, 1, tree.leaf_capacity, tree.internal_capacity,
        ids[id(tree.root)], len(nodes), tree.height,
    ))]
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
    if not 2 <= leaf_cap <= 15 or not 3 <= internal_cap <= 20:
        raise ValueError("invalid encoded capacities")
    tree = BPlusTree[int](leaf_cap, internal_cap)
    nodes: dict[int, Leaf[int] | Internal[int]] = {}
    links: dict[int, list[int]] = {}
    next_ids: dict[int, int] = {}
    for page_id, page in enumerate(pages[1:], 1):
        kind, size, next_id = HEAD.unpack_from(page)
        if kind == 1 and size <= leaf_cap:
            items = [PAIR.unpack_from(page, HEAD.size + index * PAIR.size) for index in range(size)]
            nodes[page_id] = Leaf(items)
            next_ids[page_id] = next_id
        elif kind == 2 and 2 <= size <= internal_cap and next_id == 0:
            children = [ID.unpack_from(page, HEAD.size + index * ID.size)[0] for index in range(size)]
            keys = [KEY.unpack_from(page, HEAD.size + size * ID.size + index * KEY.size)[0] for index in range(size - 1)]
            nodes[page_id] = Internal(keys)
            links[page_id] = children
        else:
            raise ValueError("invalid page header")
    seen: set[int] = set()

    def connect(page_id: int) -> Leaf[int] | Internal[int]:
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
        node = nodes[page_id]
        assert isinstance(node, Leaf)
        if next_id:
            next_node = nodes.get(next_id)
            if not isinstance(next_node, Leaf):
                raise ValueError("leaf link is not a leaf")
            node.next = next_node
    tree.height = height
    try:
        tree.validate()
    except (AssertionError, IndexError) as error:
        raise ValueError("invalid tree topology") from error
    return tree
```

## 相同点查负载的逻辑页成本

v0 的有序数组也能二分查找，不能拿它逐项比较的次数与树页数当作同一种成本。
这里两边都存储 16 字节键值记录，每个 256 字节数据页最多容纳 15 条；树的内部页
容量为 20。数组二分查找记录本次探测触及的页号，树记录根到叶所需页数，两者都
核对命中结果。每次查询开始时缓存为空，查询内同一页只计一次；元数据视为已驻内存。
这是逻辑读取模型，没有发起对应物理磁盘读取，也不保证树对所有规模都更优。

## 真正中断覆盖保存

先保存旧树，再在子进程中调用真实 `save()` 覆盖同一路径。Linux 的 `RLIMIT_FSIZE`
将文件限制为一页，并将 `SIGXFSZ` 恢复为终止进程的默认动作。保存写出超过一页时
进程被终止；旧文件已经被截断，新文件只剩元页。`load()` 拒绝它，因为元页声明的
节点数量与实际文件不符。实验不修改 `save()`，也不事后手工截断成功文件。
这个故障证明单纯 CRC 无法提供事务原子性；它不是断电或 WAL 恢复的模拟。

运行完整检查：

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/storage/bplus_tree/ -q
uv run python tests/storage/bplus_tree/replay_s02.py
```

</details>

这些命令应验证随机树、叶链、页拓扑、CRC、截断、删除借位/合并、根收缩、比较计数和每个 v0-v7 教程版本的独立打印检查。生产 B+Tree 仍需要并发控制、WAL、检查点和故障恢复；本仓库没有把这些边界隐藏起来。

将以下完整 checkpoint 保存到 `labs/storage/bplus_tree/experiments.py`，依赖仅为上面两份已冻结文件：

<!-- checkpoint: labs/storage/bplus_tree/experiments.py -->
```python
from __future__ import annotations

import json
from bisect import bisect_right
from pathlib import Path
import subprocess
import sys

from labs.storage.bplus_tree.page_file import PAGE_SIZE, load, save
from labs.storage.bplus_tree.tree import BPlusTree, Internal


def compare_accesses(keys: list[int], probes: list[int]) -> dict[str, int]:
    ordered = sorted(set(keys))
    array_pages = 0
    array_results = []
    for probe in probes:
        visited = set()
        low, high = 0, len(ordered)
        while low < high:
            middle = (low + high) // 2
            visited.add(middle // 15)
            if ordered[middle] < probe:
                low = middle + 1
            else:
                high = middle
        if low < len(ordered):
            visited.add(low // 15)
        array_results.append(low < len(ordered) and ordered[low] == probe)
        array_pages += len(visited)
    tree = BPlusTree[int](15, 20)
    for key in keys:
        tree.insert(key, key)
    tree_nodes = 0
    tree_results = []
    for probe in probes:
        node = tree.root
        while isinstance(node, Internal):
            tree_nodes += 1
            node = node.children[bisect_right(node.keys, probe)]
        tree_nodes += 1
        tree_results.append(any(key == probe for key, _ in node.items))
    assert array_results == tree_results
    return {
        "probes": len(probes),
        "array_page_reads": array_pages,
        "tree_page_reads": tree_nodes,
    }


def interrupted_save(path: Path) -> int:
    import signal

    tree = BPlusTree[int](3, 3)
    tree.insert(-1, -1)
    save(tree, path)
    child_code = """
import resource
import signal
import sys
from pathlib import Path
from labs.storage.bplus_tree.page_file import PAGE_SIZE, save
from labs.storage.bplus_tree.tree import BPlusTree

tree = BPlusTree[int](3, 3)
for key in range(40):
    tree.insert(key, key)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_FSIZE, (PAGE_SIZE, PAGE_SIZE))
signal.signal(signal.SIGXFSZ, signal.SIG_DFL)
save(tree, Path(sys.argv[1]))
"""
    result = subprocess.run([sys.executable, "-c", child_code, str(path)], timeout=10)
    if result.returncode != -signal.SIGXFSZ:
        raise RuntimeError(f"save was not interrupted by file-size limit: {result.returncode}")
    assert path.stat().st_size == PAGE_SIZE
    try:
        load(path)
    except ValueError:
        return path.stat().st_size
    raise AssertionError("partial save was accepted")


def main() -> None:
    from tempfile import TemporaryDirectory

    report = compare_accesses(list(range(1000)), [17, 500, 999])
    with TemporaryDirectory() as directory:
        partial_bytes = interrupted_save(Path(directory) / "tree.pages")
    print(json.dumps({**report, "partial_bytes": partial_bytes}, sort_keys=True))


if __name__ == "__main__":
    main()
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/storage/bplus_tree/test_s02_experiments.py -q
```

</details>

```bash
uv run python -m labs.storage.bplus_tree.experiments
```

输出包含同一组查询的 `array_page_reads`、`tree_page_reads` 以及失败保存后的
`partial_bytes=256`。比较具体计数，不把某一次优劣推广为所有负载的结论。

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.bplus_tree.experiments import compare_accesses, interrupted_save

report = compare_accesses(list(range(1000)), [17, 500, 999, 1001])
assert report["probes"] == 4
assert report["array_page_reads"] > 0 and report["tree_page_reads"] > 0
assert compare_accesses([1, 2], [1, 2, 3]) == {
    "probes": 3, "array_page_reads": 3, "tree_page_reads": 3,
}
with TemporaryDirectory() as directory:
    assert interrupted_save(Path(directory) / "tree.pages") == 256
print(report)
PY
```

```bash
uv run python - <<'PY'
from labs.storage.bplus_tree.tree import BPlusTree

tree = BPlusTree[int](3, 3)
for key in range(40):
    tree.insert(key, key * 10)
assert tree.scan(7, 13) == [(key, key * 10) for key in range(7, 14)]
for key in range(40):
    assert tree.delete(key)
assert tree.height == 1 and tree.validate()
print("v7 assembled behavior ok")
PY
```
