# S02 v0：先用有序数组建立参考答案

商品按主键查询，还需要按主键范围翻页。B-Tree 把键和值放在多个节点，B+Tree 通常把值集中在叶子并连接叶子；本系列选择 B+Tree。先从最小的有序数组开始，因为它是之后每次树结构改造都必须保持的参考行为。

数组模型包含整数主键与泛型值，例子使用字符串值；重复键覆盖旧值。插入新键时后方元素需要移动，`insert` 返回移动数量；这不是硬件 I/O 计数，只是让插入成本可见。暂不支持删除、范围扫描和持久化。

在 `[20, 40]` 中插入 30，必须把 40 向右移动；直接 append 会破坏有序不变量。`bisect_left` 找到第一个不小于 key 的位置，然后检查是否真的相等。

<!-- checkpoint: labs/storage/bplus_tree/array_index.py -->
```python
from bisect import bisect_left
from typing import Generic, TypeVar

Value = TypeVar("Value")


class OrderedIndex(Generic[Value]):
    def __init__(self) -> None:
        self.keys: list[int] = []
        self.values: list[Value] = []

    def get(self, key: int) -> Value | None:
        position = bisect_left(self.keys, key)
        if position == len(self.keys) or self.keys[position] != key:
            return None
        return self.values[position]

    def insert(self, key: int, value: Value) -> int:
        position = bisect_left(self.keys, key)
        if position < len(self.keys) and self.keys[position] == key:
            self.values[position] = value
            return 0
        self.keys.insert(position, key)
        self.values.insert(position, value)
        return len(self.keys) - position - 1
```

运行检查：

```bash
uv run python - <<'PY'
from labs.storage.bplus_tree.array_index import OrderedIndex

index = OrderedIndex()
assert index.get(7) is None
assert index.insert(20, "twenty") == 0
assert index.insert(40, "forty") == 0
assert index.insert(30, "thirty") == 1
assert index.keys == [20, 30, 40]
assert index.get(30) == "thirty"
assert index.insert(30, "updated") == 0
assert index.keys == [20, 30, 40]
assert index.get(30) == "updated"
print("v0 ordered reference ok")
PY
```

这里冻结了键升序、键值位置对应和重复键覆盖。下一篇把一个叶子限制在固定容量内，容量边界会迫使我们明确页布局。
