# S05 v0：同一个属性更新两次，读哪一个？

事件处理器把z从old更新为new，查询应得到new。我们先只处理字符串键值和单进程内存，不急着写LSM目录结构。读者需要会Python字典和函数；所有命令在仓库根目录执行，先运行 `uv sync --locked`。

## 1. 列表留下了两个答案

先运行这个完整起点：

```python
entries = [("z", "old"), ("a", "first"), ("z", "new")]
found = next(value for key, value in entries if key == "z")
assert found == "old"
print(found)
```

这是可重复错误：按第一个匹配查找读到了旧值。倒着扫描能临时取新值，但列表仍保留重复记录，输出快照还要再决定哪个版本有效。当前只需要内存最新值，因此直接以键覆盖更小。

## 2. 覆盖写入，再输出有序快照

把起点替换为：

```python
values = {}
for key, value in [("z", "old"), ("a", "first"), ("z", "new")]:
    values[key] = value
assert values["z"] == "new"
assert sorted(values.items()) == [("a", "first"), ("z", "new")]
```

这里的dict不是有序树，我们在导出时排序。put/get平均O(1)，排序快照O(n log n)并占额外O(n)空间。这是最小教学MemTable，不宣称生产LSM常用跳表/树的复杂度。

## 3. 冻结完整内存接口

下面完整新建 `labs/storage/lsm/memtable.py`。put要求字符串，get缺失为None（因此空字符串仍是有效值），items返回独立列表快照。类只封装刚才的三种操作，没有未来版本号或文件逻辑。

<!-- checkpoint: labs/storage/lsm/memtable.py -->

```python
from __future__ import annotations


class MemTable:
    """String map with sorted snapshots; sorting is deferred until items()."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def put(self, key: str, value: str) -> None:
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("key and value must be strings")
        self._values[key] = value

    def get(self, key: str) -> str | None:
        return self._values.get(key)

    def items(self) -> list[tuple[str, str]]:
        return sorted(self._values.items())


def main() -> None:
    table = MemTable()
    table.put("z", "old")
    table.put("a", "first")
    table.put("z", "new")
    print(table.items())
    print("fresh instance:", MemTable().get("z"))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.storage.lsm.memtable
uv run python -m pytest tests/storage/lsm/test_s05_memtable.py -q
```

第一条输出排序后的a/first、z/new，然后fresh instance: None。单独再次执行程序仍从空映射开始；不存在隐含持久化。测试还会先取items，再put另一键，确认原快照不被修改。

这个版本只能保存进程内最新状态。下一版保持接口含义，把一次排序快照刷成可在新进程打开的不可变文件。
