# S05 v3：把删除作为事实保存下来

v2的缺失代表“继续查旧文件”。如果删除仅从新文件省略k，查询仍会从old.sst读回old。删除必须是明确命中，命中后终止搜索，才能阻止旧值复活。

先在仓库根目录将下面代码存为临时检查脚本并用 `uv run python` 执行。它只使用上一版接口，在TemporaryDirectory中展示省略键并不能删除旧值；运行后自动清理自己的目录。

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.lsm.sstable import SSTable
from labs.storage.lsm.versions import VersionedStore

with TemporaryDirectory() as directory:
    root = Path(directory)
    old = SSTable.create(root / "old.sst", {"k": "old"})
    newer = SSTable.create(root / "new.sst", {})
    result = VersionedStore([newer.path, old.path]).get("k")
    assert result == "old"
    print("omission resurrects:", result)
```

输出 `omission resurrects: old` 是本版要修复的具体错误。新要求不是换搜索顺序，而是让查询知道“新文件明确删除了这个键”。

## 1. 普通字符串不能充当删除标记

业务值允许任意字符串。使用__TOMBSTONE__会把同名正常值误删，空字符串也不能用作标记。我们增加结构化记录：["value", text]表示正常字符串，["delete"]表示删除。create接收Mapping[str,str|None]，其中None是调用者明确删除，字符串仍全部合法。

SSTable v1底层仍存字符串，TombstoneStore.create用json.dumps把记录编码为字符串载荷。底层再编码[key,载荷]是两层有意的格式：第一层负责有序键值文件，第二层负责值或删除语义。这不是旧格式兼容适配器；v3的文件必须全部由TombstoneStore.create生成，不能把v2原始字符串文件混入。教程在新临时目录重新创建old/new，不偷偷迁移已有文件。

## 2. 命中删除即停止

get仍按新到旧查找。底层返回None才代表文件中没键，可继续；找到载荷后解析标记，delete返回None且终止，value返回原字符串。未知tag、损坏JSON或错误字段形状报错，不当作缺失。业务字符串["delete"]被包在value记录里，因此不会被误判。

先在old里写k=old，再在new里写k=None；重新打开也应该返回None。另建更晚文件put(k,"reborn")，放在删除文件之前，则允许重新创建；这不叫旧值复活，因为更晚put是新业务操作。

## 3. 完整删除检查点

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

完整新建 `labs/storage/lsm/tombstones.py`：

<!-- checkpoint: labs/storage/lsm/tombstones.py -->

```python
from __future__ import annotations

from collections.abc import Iterable, Mapping
import argparse
import json
from pathlib import Path

from labs.storage.lsm.sstable import SSTable


class TombstoneStore:
    """Newest-first files whose values encode ['value', text] or ['delete']."""

    def __init__(self, files: Iterable[Path]) -> None:
        self._files = [SSTable(path) for path in files]

    @staticmethod
    def create(path: Path, entries: Mapping[str, str | None]) -> SSTable:
        encoded: dict[str, str] = {}
        for key, value in entries.items():
            if value is not None and not isinstance(value, str):
                raise TypeError("values must be strings or None for deletion")
            record = ["delete"] if value is None else ["value", value]
            encoded[key] = json.dumps(record, ensure_ascii=False)
        return SSTable.create(path, encoded)

    def get(self, key: str) -> str | None:
        for table in self._files:
            encoded = table.get(key)
            if encoded is None:
                continue
            record = json.loads(encoded)
            if record == ["delete"]:
                return None
            if isinstance(record, list) and len(record) == 2 and record[0] == "value" and isinstance(record[1], str):
                return record[1]
            raise ValueError("expected tagged value or delete record")
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    old, new = args.directory / "old.sst", args.directory / "new.sst"
    if args.create:
        TombstoneStore.create(old, {"k": "old", "keep": "yes"})
        TombstoneStore.create(new, {"k": None, "sentinel": "__TOMBSTONE__", "empty": "", "json": '["delete"]'})
    store = TombstoneStore([new, old])
    print([store.get(key) for key in ("k", "keep", "sentinel", "empty", "json", "missing")])


if __name__ == "__main__":
    main()
```

创建独立目录，两个命令分别启动新进程；第二次没有--create，必须只从文件恢复：

```bash
lsm_demo_dir=$(mktemp -d)
uv run python -m labs.storage.lsm.tombstones "$lsm_demo_dir" --create
uv run python -m labs.storage.lsm.tombstones "$lsm_demo_dir"
uv run python -m pytest tests/storage/lsm/test_s05_versions.py -q
```

两个进程均输出[None, 'yes', '__TOMBSTONE__', '', '["delete"]', None]。k删除保持，keep回退旧文件，三种特殊字符串保留。测试还验证更晚put遮蔽删除和错误tag不能伪装缺失。

所有创建仍拒绝覆盖，成功读取不代表断电持久性：v1没有fsync。调用者给出的文件列表不是manifest，不能自动发现新文件。实验后仅清理本次临时目录中的old.sst/new.sst。
冻结持久删除语义；下一版合并时必须保留这个遮蔽关系，不能提前丢弃仍挡住旧文件的tombstone。
