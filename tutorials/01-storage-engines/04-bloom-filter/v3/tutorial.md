# S04 v3：让 Bloom Filter 守在真实 SSTable 查询之前

前置是 [v2](../v2/tutorial.md) 和 S05 v1 的不可变 SSTable。本篇使用同一个 SSTable.create、items、get 实现：UTF-8 JSONL 的每行是 [字符串键,字符串值]，严格按键递增。get 目前会扫描完整文件，所以大量缺失查询仍有明显应用读取成本。

## 1. 过滤器必须属于这一份文件

若文件里有 a、b，但调用者只提供 [a] 构建过滤器，查询 b 会被错误跳过。这是假阴性，不能用“过滤器允许误差”解释。构造器因此不接受独立键列表，而调用同一表的 items 遍历所有真实键。

文件在对象生命周期内不可变；外部覆盖同一路径、修改内容会使过滤器过期，违反合同。重开时重新遍历构建，不复用未知来源的位数组。SSTable.create 拒绝覆盖已有文件，但操作系统权限仍允许外部直接修改，教程没有提供文件系统强制隔离。

构建读取整个文件一次，不是免费操作。build_reads 表示初始化扫描次数；query_reads 只统计可能存在后实际进入 get 的扫描次数。过滤器的 bytes_used 仍然只是位数组载荷。统计应用打开/扫描次数，不声称设备物理 I/O 数。

## 2. 只有确定不存在才提前返回

query 返回 (值或 None,本次表读取次数)。False 直接返回 (None,0)；True 必须调用 SSTable.get，即使它最后返回 None。空字符串是合法值，不能使用 if value 判断是否找到。

为了验证 True 分支真的查了文件，用 bits=1、hashes=1。插入任何键后唯一位为 1，于是所有查询都返回“可能存在”。不存在的键仍应返回 None，且 reads=1；这个强制碰撞比碰巧找到一个误报字符串更稳定。

以下三个文件形成完整检查点。第一份是冻结的 S05 v1 依赖，按原实现复制，不在本篇重写文件格式或编造替代接口。filter.py 保留 v2；新增 table.py 负责过滤与统计。

将下面的完整代码保存为 `labs/storage/lsm/sstable.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/lsm/sstable.py -->
```python
from __future__ import annotations

from collections.abc import Iterator, Mapping
import json
import os
from pathlib import Path
import tempfile


class SSTable:
    """Immutable sorted JSONL file; point reads scan all records in this version."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def create(cls, path: Path, entries: Mapping[str, str]) -> SSTable:
        records = list(entries.items())
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in records):
            raise TypeError("keys and values must be strings")
        records.sort()
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as target:
            temporary = Path(target.name)
            try:
                for key, value in records:
                    target.write(json.dumps([key, value], ensure_ascii=False) + "\n")
                target.flush()
                os.link(temporary, path)
            finally:
                temporary.unlink()
        return cls(path)

    def items(self) -> Iterator[tuple[str, str]]:
        previous: str | None = None
        with self.path.open(encoding="utf-8") as source:
            for line in source:
                record = json.loads(line)
                if not isinstance(record, list) or len(record) != 2 or not all(isinstance(value, str) for value in record):
                    raise ValueError("expected [string key, string value]")
                key, value = record
                if previous is not None and key <= previous:
                    raise ValueError("keys must be strictly increasing")
                previous = key
                yield key, value

    def get(self, key: str) -> str | None:
        found: str | None = None
        for stored, value in self.items():
            if stored == key:
                found = value
        return found


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    if args.create:
        SSTable.create(args.path, {"z": "latest", "a": "first"})
    print(list(SSTable(args.path).items()))


if __name__ == "__main__":
    main()
```

将下面的完整代码保存为 `labs/storage/bloom/filter.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/bloom/filter.py -->
```python
from __future__ import annotations

from hashlib import blake2b
import math


class BloomFilter:
    def __init__(self, bits: int, hashes: int) -> None:
        if bits < 1 or hashes < 1:
            raise ValueError("bits and hashes must be positive")
        self.bits = bits
        self.hashes = hashes
        self.array = bytearray((bits + 7) // 8)

    def _positions(self, key: str) -> list[int]:
        digest = blake2b(key.encode("utf-8"), digest_size=16).digest()
        first = int.from_bytes(digest[:8], "little")
        second = int.from_bytes(digest[8:], "little") | 1
        return [(first + index * second) % self.bits for index in range(self.hashes)]

    def add(self, key: str) -> None:
        for position in self._positions(key):
            self.array[position // 8] |= 1 << (position % 8)

    def might_contain(self, key: str) -> bool:
        return all(self.array[position // 8] & (1 << (position % 8)) for position in self._positions(key))

    @property
    def bytes_used(self) -> int:
        return len(self.array)


def theoretical_false_positive_rate(bits: int, hashes: int, inserted: int) -> float:
    if bits < 1 or hashes < 1 or inserted < 0:
        raise ValueError("positive bits/hashes and nonnegative inserted required")
    return (1 - math.exp(-hashes * inserted / bits)) ** hashes
```

将下面的完整代码保存为 `labs/storage/bloom/table.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/bloom/table.py -->
```python
from pathlib import Path

from labs.storage.bloom.filter import BloomFilter
from labs.storage.lsm.sstable import SSTable


class ImmutableTable:
    def __init__(self, path: Path, bits: int = 1024, hashes: int = 4) -> None:
        self.path = path
        self.table = SSTable(path)
        self.build_reads = 0
        self.query_reads = 0
        self.filter = BloomFilter(bits, hashes)
        self.build_reads += 1
        for key, _ in self.table.items():
            self.filter.add(key)

    def query(self, key: str) -> tuple[str | None, int]:
        if not self.filter.might_contain(key):
            return None, 0
        self.query_reads += 1
        return self.table.get(key), 1
```

## 3. 比较相同结果，再计算省下的读取

下面所有文件在临时目录中。原始表的基线查询读取次数为请求数，因为 S05 v1 每次 get 都完整扫描一次。比较时先计算参考值，再构建过滤器，所以参考查询不会污染它自己的计数。构建耗费单独输出。

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.lsm.sstable import SSTable
from labs.storage.bloom.table import ImmutableTable

with TemporaryDirectory() as directory:
    path = Path(directory) / "table.jsonl"
    records = {f"key-{index:03}": str(index) for index in range(100)}
    records["empty-value"] = ""
    records["订单"] = "值"
    original = SSTable.create(path, records)
    keys = list(records) + [f"absent-{index}" for index in range(200)]
    expected = [original.get(key) for key in keys]
    table = ImmutableTable(path, bits=8192, hashes=4)
    assert table.build_reads == 1
    actual = [table.query(key)[0] for key in keys]
    assert actual == expected
    assert table.query_reads < len(keys)
    assert table.query("empty-value") == ("", 1)
    print("baseline query scans", len(keys))
    print("filter build scans", table.build_reads)
    print("filtered query scans before extra empty-value check", table.query_reads - 1)
    saturated = ImmutableTable(path, bits=1, hashes=1)
    assert saturated.query("definitely-absent") == (None, 1)
    assert saturated.query("订单") == ("值", 1)
    assert saturated.build_reads == 1 and saturated.query_reads == 2
    reopened = ImmutableTable(path)
    assert all(reopened.query(key)[0] == value for key, value in records.items())
    print("v3: results identical; false positives still read the SSTable")
PY
```

预期基线 302 次查询扫描，过滤器构建 1 次扫描；过滤查询少于 302 次，所有真实键和空值保持一致。具体假阳性次数由固定键与参数决定，但不作为概率模型必须达到的百分比断言。

本次没有持久化过滤器，也没有处理更新、删除标记、多版本可见性。后续 S05 增加多表和删除标记时，过滤器仍只能跳过不含该键的表：如果表里存在 tombstone，该键也必须加入过滤器。不能让 Bloom Filter 决定值的新旧关系。

