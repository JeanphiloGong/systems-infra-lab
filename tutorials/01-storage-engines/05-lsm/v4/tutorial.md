# S05 v4：合并文件时，删除不能被合并掉

v3每次刷写都增加不可变文件。同一键散落多个版本，缺失查询可能扫描全部文件。现在把一组文件合并成一个，但最重要的目标是读取结果不变，而不是尽快删文件。

前置[v3](../v3/tutorial.md)。输入是静止的、新到旧排列的路径列表以及连续区间[start,stop)，输出是替换该区间后的新列表。代码不扫描目录猜版本，也不删除输入或写manifest。这里的“最新”由调用者给出的文件顺序定义。

## 1. 先看一个看似合理的错误

如果合并时把删除记录当作“无需写出的空值”，文件更小了，但未参与合并的旧文件还可能保留原值。下面完整脚本只使用v3接口，在仓库根目录用 `uv run python 文件路径` 运行：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.lsm.tombstones import TombstoneStore

with TemporaryDirectory() as directory:
    root = Path(directory)
    old = TombstoneStore.create(root / "old.sst", {"k": "old"}).path
    deleted = TombstoneStore.create(root / "deleted.sst", {"k": None}).path
    assert TombstoneStore([deleted, old]).get("k") is None
    wrong = TombstoneStore.create(root / "wrong.sst", {}).path
    result = TombstoneStore([wrong, old]).get("k")
    assert result == "old"
    print("premature drop resurrects:", result)
```

输出 `premature drop resurrects: old`。原来的[deleted,old]返回None，把deleted替换为不含k的新文件之后却返回old。这个错误不需要崩溃或并发：合并过程丢失了阻挡旧值的事实。

## 2. 保留最新记录，而不是最新非空值

对所选文件按原优先级遍历，首次遇到某键就保留其结构化记录，包括delete。后来的同键都更旧，不得覆盖第一次结果。实现使用dict[str,str|None]暂存解码值，None是删除标记，空字符串仍是普通值。

每条选中文件记录都先验证tag，即使它的键已被更新文件遮蔽也不跳过格式检查；损坏输入导致失败，不能悄悄产出“合并成功”的文件。最终通过TombstoneStore.create重新编码和排序，所以输出依然满足v1的严格有序文件格式。

为什么只接收连续区间？合并[最新,最旧]但跳过中间文件时，不同键可能需要处于中间文件的不同优先级；单个输出文件不能放在一个位置就普遍保持语义。连续区间则能直接在start位置替换，前后的文件次序不变。

本版全部选中键进入内存，空间O(唯一键数)，输出还需排序；这是最小完整合并，不是流式多路归并。性能与放大测量留给v7。

## 3. 什么时候可以删除tombstone？

如果stop小于文件列表长度，外面还有更旧文件，我们保守地保留所有删除标记。即便某个键实际上没在旧文件出现，本版也不额外扫描证明它不存在。

如果stop等于列表长度，所选区间覆盖了所有更旧文件，就可以在输出中移除delete：对应旧值也在这次替换中被移除，不会从外部更旧文件重新出现。全量合并是此规则的特例；从中间开始合并最旧后缀也安全，因为外面只剩更高优先级文件。

这个判断成立的前提是files确实是当前完整、稳定的读取集合。若调用者遗漏更旧文件，或之后把被替换的旧文件重新加入列表，就破坏了前提；这里没有manifest替调用者证明这些条件。

## 4. 组装完整检查点

先保留两个冻结依赖。下面完整列出，以便在独立目录重建，不改变v1/v3格式。

完整 `labs/storage/lsm/sstable.py`：

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

完整 `labs/storage/lsm/tombstones.py`：

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

完整 `labs/storage/lsm/compaction.py`：

<!-- checkpoint: labs/storage/lsm/compaction.py -->

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from labs.storage.lsm.sstable import SSTable
from labs.storage.lsm.tombstones import TombstoneStore


def compact(files: list[Path], start: int, stop: int, output: Path) -> list[Path]:
    """Replace a contiguous newest-first slice; retain all input files on disk."""
    if not 0 <= start < stop <= len(files):
        raise ValueError("expected a nonempty in-bounds [start, stop) range")
    latest: dict[str, str | None] = {}
    for path in files[start:stop]:
        for key, encoded in SSTable(path).items():
            record = json.loads(encoded)
            if record == ["delete"]:
                value = None
            elif isinstance(record, list) and len(record) == 2 and record[0] == "value" and isinstance(record[1], str):
                value = record[1]
            else:
                raise ValueError("expected tagged value or delete record")
            if key not in latest:
                latest[key] = value
    if stop == len(files):
        latest = {key: value for key, value in latest.items() if value is not None}
    TombstoneStore.create(output, latest)
    return files[:start] + [output] + files[stop:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    old = args.directory / "old.sst"
    deleted = args.directory / "deleted.sst"
    new = args.directory / "new.sst"
    partial = args.directory / "partial.sst"
    full = args.directory / "full.sst"
    if args.create:
        TombstoneStore.create(old, {"k": "old", "keep": "old"})
        TombstoneStore.create(deleted, {"k": None})
        TombstoneStore.create(new, {"keep": "new"})
        after_partial = compact([new, deleted, old], 0, 2, partial)
        compact(after_partial, 0, 2, full)
    print("partial:", TombstoneStore([partial, old]).get("k"), SSTable(partial).get("k"))
    print("full:", TombstoneStore([full]).get("k"), SSTable(full).get("k"))
    print("keep:", TombstoneStore([full]).get("keep"))


if __name__ == "__main__":
    main()
```

compact先拒绝空/越界区间，再读完和解码，最后创建输出；只有创建成功才返回新列表。已有输出拒绝覆盖，所有输入文件保留。这保证普通异常不会破坏原读取集合，但尚未解决进程崩溃后应选择哪个集合。v5会处理该发布问题，不能把当前返回的Python列表当持久清单。

main为我们创建old、deleted、new：部分合并[new,deleted]必须保留k删除；再把[partial,old]全量合并，此时k删除可安全丢弃。它把两条路径组合都显式传给查询，另一个进程用同样列表重开。

```bash
uv sync --locked
compact_demo_dir=$(mktemp -d)
uv run python -m labs.storage.lsm.compaction "$compact_demo_dir" --create
uv run python -m labs.storage.lsm.compaction "$compact_demo_dir"
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/storage/lsm/test_s05_compaction.py -q
```

</details>

两个进程均应输出：

```text
partial: None ["delete"]
full: None None
keep: new
```

partial中逻辑查询缺失，但底层记录仍为delete；full里连记录本身也不存在，逻辑结果依旧缺失。keep的新值一直保留。参考分支的历史测试还覆盖全部六种连续区间、更新文件优先级、删除后新put、非法范围、坏tag及拒绝覆盖。

本版不清理旧文件，也没有并发读取者跟踪或WAL；实验结束后可以清理本次临时目录。冻结的是合并语义与删除标记安全边界，下一版再讨论如何把新的文件集合可靠地发布。
