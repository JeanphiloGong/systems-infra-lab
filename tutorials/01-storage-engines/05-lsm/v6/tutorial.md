# S05 v6：把 WAL 和 Bloom 接回同一个 LSM

v5 能重开已发布的 SSTable 集合，但尚未 flush 的更新只在内存。客户端刚收到 put 成功，进程退出就可能丢数据。另一方面，缺失键仍逐个扫描表。本版分别解决这两条路径，同时保留任意字符串、空字符串、删除标记和 MANIFEST 的语义。

先完成 [S05 v5](../v5/tutorial.md)、[S03 v1](../../03-wal-and-recovery/v1/tutorial.md) 的 `labs/storage/wal/framing.py`，以及 [S04 v3](../../04-bloom-filter/v3/tutorial.md) 的 `labs/storage/bloom/filter.py`、`table.py`。继续使用已有 `sstable.py`、`tombstones.py`、`manifest.py`；S04 的 SSTable 与这里格式相同，不另造 key=value 文件。

本版限本地 POSIX 文件系统、单写者。SSTable 仍是 `[key, encoded_string]` JSONL，内部 encoded_string 是 value/delete 标签的 JSON。Bloom 只减少查询时打开 SSTable 的次数；启动重建 Bloom 仍扫描全表，计数不是物理磁盘 I/O。

## 1. 在修改内存前同步 WAL

写入顺序必须是 encode → append → flush/fsync → 更新内存 → 返回。这里的记录是覆盖或删除同一个键，重复回放结果相同。不要把这条规则直接用于余额加减等非幂等操作。

新建 `labs/storage/lsm/wal.py`，下面是完整 checkpoint。复用 S03 的 framing：它先检查长度和反码，再判断帧是否完整，最后检查 CRC。完整头损坏必须报错；只有结尾不完整的帧才能截断。`replay` 先验证全部记录，再执行截断，因此前面损坏时不会修改原 WAL。

<!-- checkpoint: labs/storage/lsm/wal.py -->

```python
from __future__ import annotations

import os
from pathlib import Path

from labs.storage.wal.framing import decode, encode


class WAL:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, key: str, value: str | None) -> None:
        if not isinstance(key, str) or (value is not None and not isinstance(value, str)):
            raise TypeError("invalid WAL record")
        with self.path.open("ab") as stream:
            stream.write(encode({"key": key, "value": value}))
            stream.flush()
            os.fsync(stream.fileno())

    def replay(self) -> list[tuple[str, str | None]]:
        if not self.path.exists():
            return []
        frames, valid_end, torn = decode(self.path.read_bytes())
        records: list[tuple[str, str | None]] = []
        for record in frames:
            if set(record) != {"key", "value"} or not isinstance(record["key"], str) or (record["value"] is not None and not isinstance(record["value"], str)):
                raise ValueError("invalid WAL record")
            records.append((record["key"], record["value"]))
        if torn:
            with self.path.open("r+b") as stream:
                stream.truncate(valid_end)
                stream.flush()
                os.fsync(stream.fileno())
        return records

    def clear(self) -> None:
        with self.path.open("wb") as stream:
            stream.flush()
            os.fsync(stream.fileno())
```

## 2. 按 MANIFEST 恢复，再覆盖 WAL

新建 `labs/storage/lsm/v6.py`。`RecoveredStore` 是前五版组件的读写入口：初始化读取 MANIFEST 指定的文件，为每个 SSTable 构建 ImmutableTable，最后回放 WAL 到内存。不能扫描目录把未发布的孤儿文件当成新版本。

`get` 先看内存；缺失才按新到旧访问真实 SSTable。Bloom 的肯定结果还需查表，否定结果跳过表；删除标记要立刻返回 None，不能继续找旧值。`last_query_reads` 累计真实调用表查询的次数。

`flush` 的顺序是写新 SSTable → 发布包含新表的 MANIFEST → 清空 WAL → 清空内存。发布前崩溃由旧表加 WAL 恢复；发布后、清 WAL 前会重复回放，但覆盖/删除是幂等的；清 WAL 后由新表恢复。任何写入异常后当前对象停止写，必须重开以重新确定持久状态。故障开关只用于后面的独立子进程实验。

<!-- checkpoint: labs/storage/lsm/v6.py -->

```python
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from labs.storage.bloom.table import ImmutableTable
from labs.storage.lsm.manifest import manifest_paths, publish
from labs.storage.lsm.tombstones import TombstoneStore
from labs.storage.lsm.wal import WAL


class RecoveredStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        if not (directory / "MANIFEST").exists():
            if any(directory.iterdir()):
                raise ValueError("nonempty directory has no MANIFEST")
            publish(directory, [])
        self.wal = WAL(directory / "write.wal")
        if not self.wal.path.exists():
            self.wal.clear()
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        names = json.loads((directory / "MANIFEST").read_text(encoding="utf-8"))
        self.files = manifest_paths(directory, names)
        self.tables = [ImmutableTable(path) for path in self.files]
        self.values: dict[str, str | None] = {}
        for key, value in self.wal.replay():
            self.values[key] = value
        self.failed = False
        self.last_query_reads = 0

    def put(self, key: str, value: str | None) -> None:
        if self.failed:
            raise RuntimeError("reopen store after a write failure")
        if not isinstance(key, str) or (value is not None and not isinstance(value, str)):
            raise TypeError("key/value must be strings; None means delete")
        try:
            self.wal.append(key, value)
        except Exception:
            self.failed = True
            raise
        self.values[key] = value

    def get(self, key: str) -> str | None:
        self.last_query_reads = 0
        if key in self.values:
            return self.values[key]
        for table in self.tables:
            encoded, reads = table.query(key)
            self.last_query_reads += reads
            if encoded is None:
                continue
            record = json.loads(encoded)
            if record == ["delete"]:
                return None
            if isinstance(record, list) and len(record) == 2 and record[0] == "value" and isinstance(record[1], str):
                return record[1]
            raise ValueError("invalid tagged record")
        return None

    def flush(self, crash: str | None = None) -> Path | None:
        if crash not in {None, "before_publish", "after_publish", "after_wal_clear"}:
            raise ValueError("unknown crash point")
        if self.failed:
            raise RuntimeError("reopen store after a write failure")
        if not self.values:
            return None
        try:
            path = self.directory / (uuid4().hex + ".sst")
            TombstoneStore.create(path, self.values)
            if crash == "before_publish":
                os._exit(81)
            publish(self.directory, [path] + self.files)
            if crash == "after_publish":
                os._exit(82)
            self.wal.clear()
            if crash == "after_wal_clear":
                os._exit(83)
            self.files.insert(0, path)
            self.tables.insert(0, ImmutableTable(path))
            self.values.clear()
            return path
        except Exception:
            self.failed = True
            raise
```

## 3. 验证恢复的是同一份数据

新建 `labs/storage/lsm/check_v6.py`。先写旧值并 flush，再删除它，同时加入包含等号、换行、中文以及空值的记录；重开和 flush 后结果必须一致。检查同时覆盖新进程读取、真正撕裂尾帧、三种完整帧损坏与三个 flush 发布边界。

<!-- checkpoint: labs/storage/lsm/check_v6.py -->

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys

from labs.storage.lsm.v6 import RecoveredStore
from labs.storage.wal.framing import encode


def run():
    with TemporaryDirectory() as folder:
        root = Path(folder)
        store = RecoveredStore(root / "normal")
        store.put("gone", "old")
        store.put("stable", "yes")
        store.flush()
        store.put("gone", None)
        store.put("a=b\n中文", "value=\n")
        store.put("empty", "")
        expected = {"gone": None, "stable": "yes", "a=b\n中文": "value=\n", "empty": ""}
        reopened = RecoveredStore(store.directory)
        assert {key: reopened.get(key) for key in expected} == expected
        reopened.flush()
        reader = """import json,sys
from pathlib import Path
from labs.storage.lsm.v6 import RecoveredStore
s=RecoveredStore(Path(sys.argv[1]))
print(json.dumps({key:s.get(key) for key in json.loads(sys.argv[2])}))
"""
        child = subprocess.run([sys.executable, "-c", reader, str(store.directory), json.dumps(list(expected))],
                               check=True, capture_output=True, text=True, timeout=10)
        assert json.loads(child.stdout) == expected
        reads = 0
        for index in range(100):
            assert reopened.get("missing-" + str(index)) is None
            reads += reopened.last_query_reads
        assert reads < 100 * len(reopened.files)

        # Only a genuine incomplete trailing frame may be removed.
        for damage in ("torn", "length", "complement", "checksum"):
            case = RecoveredStore(root / damage)
            case.put("first", "acknowledged")
            case.put("second", "also-acknowledged")
            path = case.wal.path
            confirmed = path.read_bytes()
            raw = bytearray(confirmed)
            if damage == "torn":
                raw += encode({"key": "unacknowledged", "value": "tail"})[:-2]
            elif damage == "length":
                raw[0] ^= 0x40
            elif damage == "complement":
                raw[4] ^= 1
            else:
                raw[-1] ^= 1
            path.write_bytes(raw)
            if damage == "torn":
                recovered = RecoveredStore(case.directory)
                assert recovered.get("first") == "acknowledged"
                assert recovered.get("second") == "also-acknowledged"
                assert recovered.get("unacknowledged") is None
                assert path.read_bytes() == confirmed
            else:
                try:
                    RecoveredStore(case.directory)
                except ValueError:
                    assert path.read_bytes() == raw
                else:
                    raise AssertionError("corruption was silently discarded")

        for point, code in (("before_publish", 81), ("after_publish", 82), ("after_wal_clear", 83)):
            case = RecoveredStore(root / point)
            case.put("gone", "old")
            case.put("stable", "yes")
            case.flush()
            worker = """import sys
from pathlib import Path
from labs.storage.lsm.v6 import RecoveredStore
s=RecoveredStore(Path(sys.argv[1]))
s.put('gone',None);s.put('new','saved')
s.flush(crash=sys.argv[2])
"""
            killed = subprocess.run([sys.executable, "-c", worker, str(case.directory), point], timeout=10)
            assert killed.returncode == code
            recovered = RecoveredStore(case.directory)
            assert recovered.get("gone") is None
            assert recovered.get("stable") == "yes" and recovered.get("new") == "saved"
        print({"restart_preserved": expected, "negative_table_scans": reads,
               "corruption_rejected": 3, "flush_crash_points": 3})


if __name__ == "__main__":
    run()
```

```bash
uv run python -m labs.storage.lsm.check_v6
```

预期三种损坏都拒绝且 WAL 原字节不变，三个子进程分别以 81/82/83 退出后仍可恢复已确认写入。负查询的表扫描数应小于全部查表的 200 次；具体数量由过滤器决定，不能要求所有负查询都是零。Bloom 构建成本不在该数字中。

这个检查点保存完整读写恢复链。它没有多写者、后台合并、孤儿文件回收或断电故障注入；进程退出验证不等同于硬件断电证明。下一版就在此入口上增加合并策略与真实字节计数。
