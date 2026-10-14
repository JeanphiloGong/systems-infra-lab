# S05 v5：重启后应该采用哪个文件集合？

v4成功合并后返回一个新的Python文件列表，但进程退出就失去这个列表。扫描目录不能恢复它：旧输入文件仍然存在，目录中也可能有尚未发布的输出文件。我们需要一份明确记录当前读取集合的manifest，而不是根据文件名猜测。

本版限定本地POSIX文件系统、单个发布者、发布期间不修改/删除的不可变SSTable。manifest是按新到旧排列的JSON文件名数组，读取者只采用它列出的文件。数据格式沿用v3，不增加WAL或后台合并。

## 1. 先把当前集合保存下来

若直接用w模式覆盖MANIFEST，进程可能在写一半时终止。下面完整检查模拟这种不完整内容，JSON无法解析，说明原地重写不能保证重启读取：

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as folder:
    path = Path(folder) / "MANIFEST"
    path.write_text('["old.sst"]', encoding="utf-8")
    path.write_text('["new.sst",', encoding="utf-8")
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("partial manifest is unreadable")
    else:
        raise AssertionError("expected broken JSON")
```

下一要求是：在新manifest完整写好前保留旧文件。临时文件MANIFEST.tmp不是可读集合；load永远只打开MANIFEST，也不尝试猜测或修复临时内容。

## 2. 完整写入，再切换名字

publish先校验文件路径确实属于给定目录，**在取basename之前**完成，避免把../outside.sst悄悄转成inside文件名。文件名必须是互不重复的直接子.sst文件，缺失文件、目录和符号链接都拒绝。空数组允许，表示空存储；格式损坏则抛ValueError，不能当空库。

manifest_paths这个共享校验函数有两个调用者：publish在写入前验证新集合，load在启动时验证持久集合。它不解释业务值，只检查路径和文件存在性；SSTable内容校验仍由其读取接口负责。

接下来逐个fsync新集合的数据文件，再fsync目录，让先前SSTable的文件名建立先于manifest发布。临时manifest写完后flush+fsync，然后同目录os.replace替换MANIFEST，最后fsync目录确认新的名字关系。若文件系统/硬件遵守这些同步语义，成功返回才表示这个协议的同步步骤完成。v1本身没有fsync，因此这里不能省略数据文件同步。

原子replace保证并发读取者看到完整旧JSON或完整新JSON，而不是半份内容。读取者拿到旧列表也可以继续读，因为本版仍不删除旧文件。固定临时文件名要求单写者；多写者互斥和读者回收均不在本版。

## 3. 在两个边界真正终止进程

异常会运行finally，不能模拟进程突然结束。因此故障开关使用os._exit(71/72)，绕过Python清理：71发生在临时文件同步后、replace前；72发生在replace后、最终目录fsync前。

两者都必须从**已经有效的旧manifest**开始。退出71后，新进程仍读old，残留MANIFEST.tmp被忽略。退出72后，在同一仍运行的操作系统上新进程读new，证明发布名字已切换。这个72实验不是断电：此时最后目录fsync尚未执行，不能据此声称机器断电后必为new。真正断电恢复仍依赖文件系统和存储设备保证。

普通异常会清理临时文件并关闭目录描述符；os._exit不做这些清理，操作系统负责回收进程资源。任何文件内容或manifest错误都直接失败，不从目录里的其他文件拼出猜测集合。

## 4. 冻结完整发布检查点

下面完整列出冻结依赖和新入口。保存到指定路径，即可在独立目录重建，不需要工作树的隐含模块。

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

完整 `labs/storage/lsm/manifest.py`：

<!-- checkpoint: labs/storage/lsm/manifest.py -->

```python
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from labs.storage.lsm.tombstones import TombstoneStore


def manifest_paths(directory: Path, names: object) -> list[Path]:
    if not isinstance(names, list):
        raise ValueError("manifest must be a list of filenames")
    paths: list[Path] = []
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".sst") or name in seen:
            raise ValueError("expected distinct direct-child .sst filenames")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("manifest file missing or not a regular local file")
        seen.add(name)
        paths.append(path)
    return paths


def publish(directory: Path, files: list[Path], crash: str | None = None) -> None:
    """Single writer on a local POSIX filesystem; input SSTables are immutable."""
    if crash not in {None, "before_publish", "after_publish"}:
        raise ValueError("unknown crash point")
    for path in files:
        if path.parent.resolve() != directory.resolve():
            raise ValueError("manifest files must be direct children")
    names = [path.name for path in files]
    paths = manifest_paths(directory, names)
    for path in paths:
        with path.open("rb") as source:
            os.fsync(source.fileno())
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
        temporary = directory / "MANIFEST.tmp"
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(names, stream)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            if crash == "before_publish":
                os._exit(71)
            os.replace(temporary, directory / "MANIFEST")
            if crash == "after_publish":
                os._exit(72)
            os.fsync(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        os.close(directory_fd)


def load(directory: Path) -> TombstoneStore:
    names = json.loads((directory / "MANIFEST").read_text(encoding="utf-8"))
    return TombstoneStore(manifest_paths(directory, names))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--create", action="store_true")
    actions.add_argument("--publish", action="store_true")
    parser.add_argument("--crash", choices=["before_publish", "after_publish"])
    args = parser.parse_args()
    if args.crash and not args.publish:
        parser.error("--crash requires --publish")
    old, new = args.directory / "old.sst", args.directory / "new.sst"
    if args.create:
        args.directory.mkdir(parents=True, exist_ok=True)
        TombstoneStore.create(old, {"k": "old", "stable": "yes"})
        TombstoneStore.create(new, {"k": "new"})
        publish(args.directory, [old])
    if args.publish:
        publish(args.directory, [new, old], args.crash)
    store = load(args.directory)
    print(json.dumps({"k": store.get("k"), "stable": store.get("stable")}))


if __name__ == "__main__":
    main()
```

main的--create创建old/new两个不可变文件，但仅发布old。--publish再发布[new,old]；普通读取不修改文件。这里只需要新旧两个集合验证发布，不再次运行v4合并；实际调用者可以把compact返回的列表直接传给publish。

从仓库根目录运行：

```bash
uv sync --locked
manifest_demo_dir=$(mktemp -d)
uv run python -m labs.storage.lsm.manifest "$manifest_demo_dir" --create
uv run python -m labs.storage.lsm.manifest "$manifest_demo_dir" --publish --crash before_publish
uv run python -m labs.storage.lsm.manifest "$manifest_demo_dir"
uv run python -m labs.storage.lsm.manifest "$manifest_demo_dir" --publish --crash after_publish
uv run python -m labs.storage.lsm.manifest "$manifest_demo_dir"
uv run python -m labs.storage.lsm.manifest "$manifest_demo_dir" --publish
uv run python -m pytest tests/storage/lsm/test_s05_manifest.py tests/storage/lsm/test_s05_manifest_replay.py -q
```

故障命令预期分别退出71和72；在启用set -e的脚本里需显式检查这些预期退出码，不能让脚本提前中止而漏掉后续读取。首次创建及71之后输出{"k":"old","stable":"yes"}，72之后及正常发布输出{"k":"new","stable":"yes"}（JSON空格不影响含义）。stable证明新列表仍包含旧文件，不只是测试单一值碰巧相同。

测试同时检查磁盘MANIFEST数组恰好是[old.sst]或[new.sst,old.sst]；格式、重复、缺失及越界路径拒绝；并从正文抽取完整依赖到干净目录，真实退出发布进程，再由另一个进程读取。只有围栏存在或同进程抛RuntimeError不算通过。

现在冻结单写者发布协议。旧文件暂不回收，故障后的临时文件不参与读取，正常下一次发布可覆盖它。后续WAL/过滤器集成仍需独立实验；不要把manifest等同事务日志。
