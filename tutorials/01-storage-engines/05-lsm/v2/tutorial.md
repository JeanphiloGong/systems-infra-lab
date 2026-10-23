# S05 v2：多个文件里，谁是最新值？

事件属性k已经刷入old.sst，随后k更新为new。v1文件不可变，所以再次刷写要创建new.sst。只查旧文件会读到old，只查新文件又会漏掉旧文件独有的keep。目标是让多个不可变文件表现成一个最新值映射。

## 1. 明确优先级输入

本版接受调用者提供的“新到旧”路径列表，不按名字或mtime猜先后，也不扫描目录。列表位置就是本版的版本优先级；重启时调用者必须提供相同顺序，文件集合的持久清单留在v5。

算法是依次调用SSTable.get，首个非None结果返回。要用is not None而非if value，否则新文件的空字符串会被当缺失，错误回退旧值。空文件集合返回None；缺失文件/损坏记录直接抛异常，不吞掉后读旧值。

## 2. 用两次刷写建立压力

old中存k=old、keep=yes、empty=old，新文件中存k=new、empty=""。按[new,old]查询应得到new、yes、空字符串；按[old,new]反过来则会读旧值，这是调用者优先级错误，不是字符串排序问题。

VersionedStore只保存SSTable列表，没有写缓冲、删除或后台线程。最坏点查扫描全部文件，本版不引入索引或合并。main增加--create便于先建立文件、再在另一个进程重读，实际读时不依赖前一个对象。

## 3. 完整多文件检查点

前置上一版，从仓库根目录运行 `uv sync --locked`。本检查点保留v1底层文件代码，完整列出以便独立重放；请勿修改它来识别删除。

完整 `labs/storage/lsm/sstable.py`（与v1相同）：

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

完整新建 `labs/storage/lsm/versions.py`：

<!-- checkpoint: labs/storage/lsm/versions.py -->

```python
from __future__ import annotations

import argparse
from pathlib import Path
from collections.abc import Iterable

from labs.storage.lsm.sstable import SSTable


class VersionedStore:
    """Newest-to-oldest immutable files; caller supplies priority order."""

    def __init__(self, files: Iterable[Path]) -> None:
        self._files = [SSTable(path) for path in files]

    def get(self, key: str) -> str | None:
        for table in self._files:
            value = table.get(key)
            if value is not None:
                return value
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    old, new = args.directory / "old.sst", args.directory / "new.sst"
    if args.create:
        SSTable.create(old, {"k": "old", "keep": "yes", "empty": "old"})
        SSTable.create(new, {"k": "new", "empty": ""})
    store = VersionedStore([new, old])
    print([store.get(key) for key in ("k", "keep", "empty", "missing")])


if __name__ == "__main__":
    main()
```

创建独立目录，两个命令分别启动新进程；第二次没有--create，必须只从文件恢复：

```bash
lsm_demo_dir=$(mktemp -d)
uv run python -m labs.storage.lsm.versions "$lsm_demo_dir" --create
uv run python -m labs.storage.lsm.versions "$lsm_demo_dir"
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/storage/lsm/test_s05_versions.py -q
```

</details>

两个进程均输出['new', 'yes', '', None]。为了检查优先级，将main中的[new, old]临时改成[old, new]，在同一目录无--create运行，应得到['old', 'yes', 'old', None]；再改回。

所有创建仍拒绝覆盖，成功读取不代表断电持久性：v1没有fsync。调用者给出的文件列表不是manifest，不能自动发现新文件。实验后仅清理本次临时目录中的old.sst/new.sst。
冻结文件顺序契约；下一版解决删除。
