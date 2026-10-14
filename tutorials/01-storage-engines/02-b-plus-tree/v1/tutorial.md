# S02 v1：把有序数组装进一个叶页

v0 的数组可以无限增长，但真实页有固定容量。先把容量设为 3：前三个键可查，第四个新键必须拒绝；重复键覆盖不需要新槽位。分裂是下一版的压力，不在本版偷偷加入。

v0 用两个平行列表保存键和值。页分裂时若只切分其中一个列表，关联就会错位；因此本版把它们组成 `(key, value)` 对，放进同一个 items 列表。后续切片移动的是完整记录。为了使用 bisect，临时提取键列表，这一步是 O(n)，所以本版不是整体 O(log n) 查找；这里页内容量很小，先保持表示直观。

覆盖已有键不需要新槽位，因此必须先检查覆盖，再检查容量。新键满页时直接抛错，列表不发生修改。以下是 `labs/storage/bplus_tree/leaf.py` 的完整检查点。

<!-- checkpoint: labs/storage/bplus_tree/leaf.py -->
```python
from bisect import bisect_left
from typing import Generic, TypeVar

Value = TypeVar("Value")


class LeafPage(Generic[Value]):
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.items: list[tuple[int, Value]] = []

    def get(self, key: int) -> Value | None:
        position = bisect_left([item[0] for item in self.items], key)
        if position == len(self.items) or self.items[position][0] != key:
            return None
        return self.items[position][1]

    def insert(self, key: int, value: Value) -> int:
        keys = [item[0] for item in self.items]
        position = bisect_left(keys, key)
        if position < len(self.items) and self.items[position][0] == key:
            self.items[position] = (key, value)
            return 0
        if len(self.items) == self.capacity:
            raise OverflowError("leaf page is full")
        moved = len(self.items) - position
        self.items.insert(position, (key, value))
        return moved
```

```bash
uv run python - <<'PY'
from labs.storage.bplus_tree.leaf import LeafPage

leaf = LeafPage(3)
assert leaf.insert(20, "a") == 0
assert leaf.insert(10, "b") == 1
assert leaf.insert(30, "c") == 0
assert leaf.items == [(10, "b"), (20, "a"), (30, "c")]
assert leaf.insert(20, "updated") == 0
assert leaf.get(20) == "updated"
assert leaf.get(99) is None
before = leaf.items.copy()
try:
    leaf.insert(40, "d")
except OverflowError:
    pass
else:
    raise AssertionError("full leaf accepted a fourth key")
assert leaf.items == before
try:
    LeafPage(0)
except ValueError:
    pass
else:
    raise AssertionError("zero capacity accepted")
print("v1 leaf capacity ok")
PY
```

预期输出 `v1 leaf capacity ok`。检查同时证明满页覆盖可行、缺失返回 None、溢出前后内容不变、容量必须为正。现在容量边界是明确的，下一篇用叶页分裂和新根继续保存所有键。
