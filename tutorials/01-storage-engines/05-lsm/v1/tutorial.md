# S05 v1：把排序快照刷成不可变文件

v0退出就失去所有事件属性。现在需要把一次MemTable快照写入文件，并在没有原内存对象的新进程读取。范围只有一个文件，不实现多文件优先级、删除、WAL或合并。

## 1. 先选能保存真实字符串的格式

直接写key+"="+value会遇到键值含等号、引号或换行的歧义。本版每行用JSON数组[key,value]，文件编码UTF8。下面可独立执行的检查保留换行和非ASCII，而不是靠split猜字段：

```python
import json
record = ["城市", "line1\nline2"]
encoded = json.dumps(record, ensure_ascii=False)
assert json.loads(encoded) == record
assert "\n" not in encoded
```

JSON把值内换行编码为转义序列，所以一行仍对应一条完整记录。键排序采用Python字符串比较，不是语言地区排序。create接收Mapping，同键覆盖由v0先完成；刷写时调用 `SSTable.create(path, dict(memtable.items()))`。

## 2. 保持排序并定义查询

create先验证键值都是字符串，复制并排序后写入。items逐行解析，只接受两个字符串组成的数组，并要求键严格递增。重复或倒序键不是另一个版本，而是当前单文件格式损坏，必须报错。

get暂时扫描整个文件，包括找到键之后的尾部，避免跳过尾部损坏。空表与缺失键返回None，空字符串返回空串。这里没有稀疏索引，点查O(n)；S04可在外面增加Bloom以跳过肯定不存在的查询，但不能改变结果。

## 3. 不可变意味着拒绝覆盖

直接打开目标w模式会截断已有文件，直接创建目标再写入又会让半成品可见。本版先在同目录临时文件写完并flush，再用os.link把完整文件发布到目标名。目标已存在时link失败，旧内容不变；finally删除临时名字。

这仅要求支持硬链接的本地POSIX文件系统，解决成功创建时的命名可见性和拒绝覆盖。没有文件/目录fsync，不提供断电持久保证；进程被杀也可能留下临时文件。多文件清单与完整崩溃发布协议仍在v5。这里只加入单文件不可变创建所需边界，不把它当完整存储引擎。

## 4. 完整单文件检查点

下面完整新建 `labs/storage/lsm/sstable.py`。SSTable(path)仅记录路径，真正读取在items/get发生，因此缺失文件在首次读取报FileNotFoundError；这是明确契约，不自动创建空文件。

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

在仓库根目录创建本次独立实验目录，然后运行两个不同Python进程：

```bash
sst_demo_dir=$(mktemp -d)
uv run python -m labs.storage.lsm.sstable "$sst_demo_dir/one.sst" --create
uv run python -m labs.storage.lsm.sstable "$sst_demo_dir/one.sst"
uv run python -m pytest tests/storage/lsm -q
```

前两条都显示[('a','first'),('z','latest')]（Python会显示空格）。第二进程没有创建数据却能读取，说明结果来自文件。第三次加--create应报FileExistsError，原文件内容不变。实验后只删除本次one.sst及其临时目录。

测试覆盖UTF8、引号、反斜杠、值内换行、空字符串、空表、无效类型、损坏排序/重复键和新进程重读。文件读取异常不会被当作“键不存在”。冻结这个API供S04集成；下一版才需要决定同一键出现在多个文件时谁更新。
