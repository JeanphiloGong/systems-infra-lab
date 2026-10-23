# S05 v7：在同一个存储上比较全量合并与两层合并

v6 已能恢复写入，但每次 flush 都增加一个 SSTable。相同的四批数据可以全部重写成一张表，也可以只把最老的 L0 表与键范围重叠的 L1 表合并。本版实现后者的最小两层规则，实际检查层内范围不重叠；它不再只是取最后两张表并称为 leveled。

前置：[v6](../v6/tutorial.md) 的全部文件，以及 [v4](../v4/tutorial.md) 的 `compaction.py`。继续使用同一个 `RecoveredStore`、MANIFEST 数组、JSONL 标签与 get/put 接口。v6 创建的表都视作 L0，合并输出用 `l1-` 文件名前缀记录层级，MANIFEST 依然是唯一的活跃集合。此命名规则属于本实验磁盘契约。

## 1. 从“多文件”推导层规则

L0 可以重叠，按新到旧读取；当 L0 达到两张时，选最老的一张下推。L1 按键范围排序，范围之间不能重叠。下推时选择所有与该 L0 范围相交的 L1 表，先读较新的 L0，再读较旧的 L1，保留每个键第一个版本。这个选择不涉及其他较新的 L0 表。

输出范围被选中范围的并集覆盖，未选 L1 范围与之不交；仍明确断言层内不重叠。局部合并保留 tombstone，避免把删除解释成缺失后继续找到旧值。全量合并复用 v4 的 compact，可以丢弃所有旧版本已被覆盖的删除标记。两者最终都通过 publish 原子替换 MANIFEST，保留旧文件以允许旧读者完成读取。

这里仅有 L0/L1，L0 容量为一张，L1 没有向 L2 下推；没有后台线程或完整多层容量调度。范围信息通过扫描 SSTable 获取，生产引擎通常存于元数据。本实验把范围扫描计入 planning_read_bytes，并与合并读字节分开报告。

## 2. 给现有入口增加 compact

替换 `labs/storage/lsm/v6.py` 为下面的完整 checkpoint。沿用路径是为了保留 v6 的调用者和恢复检查；新增的是 `compact(strategy)`，其余接口不变。先 flush 再 compact，保持本版的单写者边界。合并失败后要求重开，避免不确定发布结果下继续写。

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
from labs.storage.lsm.sstable import SSTable
from labs.storage.lsm.compaction import compact


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

    def compact(self, strategy: str) -> dict[str, int] | None:
        if strategy not in {"full", "leveled"}:
            raise ValueError("expected full or leveled")
        if self.failed:
            raise RuntimeError("reopen store after a write failure")
        if self.values:
            raise ValueError("flush before compacting")
        if not self.files:
            return None
        planning_bytes = 0
        if strategy == "full":
            selected = list(self.files)
            remaining_l0, untouched_l1 = [], []
        else:
            l0 = [path for path in self.files if not path.name.startswith("l1-")]
            l1 = [path for path in self.files if path.name.startswith("l1-")]
            # L0 tolerates one file; two trigger promotion of the oldest file.
            if len(l0) < 2:
                return None
            oldest = l0[-1]
            ranges = {}
            for path in [oldest] + l1:
                keys = [key for key, _ in SSTable(path).items()]
                planning_bytes += path.stat().st_size
                if keys:
                    ranges[path] = (keys[0], keys[-1])
            low, high = ranges[oldest]
            ordered_l1 = sorted(ranges[path] for path in l1 if path in ranges)
            assert all(left[1] < right[0] for left, right in zip(ordered_l1, ordered_l1[1:]))
            overlap = [path for path in l1 if path in ranges
                       and ranges[path][0] <= high and low <= ranges[path][1]]
            selected = [oldest] + overlap
            remaining_l0 = l0[:-1]
            untouched_l1 = [path for path in l1 if path not in overlap]
        output = self.directory / ("l1-" + uuid4().hex + ".sst")
        try:
            if strategy == "full":
                # v4 merges all older versions, so tombstones may be dropped.
                compact(self.files, 0, len(self.files), output)
            else:
                latest = {}
                for path in selected:
                    for key, tagged in SSTable(path).items():
                        latest.setdefault(key, tagged)
                # Keep the existing encoded strings, including tombstones.
                SSTable.create(output, latest)
            l1_after = untouched_l1 + [output]
            keyed = []
            for path in l1_after:
                planning_bytes += path.stat().st_size
                keys = [key for key, _ in SSTable(path).items()]
                if keys:
                    keyed.append((keys[0], keys[-1], path))
            keyed.sort()
            assert all(left[1] < right[0] for left, right in zip(keyed, keyed[1:]))
            files = remaining_l0 + [path for _, _, path in keyed]
            publish(self.directory, files)
            self.files = files
            self.tables = [ImmutableTable(path) for path in files]
        except Exception:
            self.failed = True
            raise
        return {"merge_read_bytes": sum(path.stat().st_size for path in selected),
                "merge_written_bytes": output.stat().st_size,
                "planning_read_bytes": planning_bytes,
                "input_files": len(selected), "live_files": len(self.files)}
```

## 3. 用同一份已落盘数据比较

新建 `labs/storage/lsm/check_v7.py`。先运行 v6 全部恢复检查，再将同一份已 flush 的目录复制成两份。每次合并后重开并读回全部键，包含删除、空字符串与换行；结果正确后才比较字节数。

四批数据使前两次 L0 下推不与已有 L1 相交，第三次与一张 L1 相交；输入文件数因此应为 1、1、2。若代码始终只选最后两张文件，此检查会失败。最后保留一张 L0 和两张不重叠的 L1。

<!-- checkpoint: labs/storage/lsm/check_v7.py -->

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import shutil

from labs.storage.lsm.v6 import RecoveredStore
from labs.storage.lsm.sstable import SSTable
from labs.storage.lsm.check_v6 import run as check_recovery


def run():
    check_recovery()
    with TemporaryDirectory() as folder:
        root = Path(folder)
        original = RecoveredStore(root / "original")
        batches = [{"a": "old", "b": "keep"}, {"x": "far"},
                   {"a": None, "b": "new"}, {"a=b\n中文": "", "z": "last"}]
        expected = {}
        logical_bytes = 0
        flush_bytes = 0
        for batch in batches:
            for key, value in batch.items():
                logical_bytes += len(json.dumps([key, value], ensure_ascii=False).encode("utf-8"))
                original.put(key, value)
                expected[key] = value
            path = original.flush()
            flush_bytes += path.stat().st_size
        results = {}
        for strategy in ("full", "leveled"):
            directory = root / strategy
            shutil.copytree(original.directory, directory)
            store = RecoveredStore(directory)
            totals = dict(merge_read_bytes=0, merge_written_bytes=0, planning_read_bytes=0)
            steps = []
            peak_sstable_bytes = sum(path.stat().st_size for path in directory.glob("*.sst"))
            while True:
                stats = store.compact(strategy)
                if stats is None:
                    break
                steps.append(stats)
                peak_sstable_bytes = max(peak_sstable_bytes, sum(path.stat().st_size for path in directory.glob("*.sst")))
                for name in totals:
                    totals[name] += stats[name]
                store = RecoveredStore(directory)
                assert {key: store.get(key) for key in expected} == expected
                l1_ranges = []
                for path in store.files:
                    if path.name.startswith("l1-"):
                        keys = [key for key, _ in SSTable(path).items()]
                        l1_ranges.append((keys[0], keys[-1]))
                assert all(left[1] < right[0] for left, right in zip(l1_ranges, l1_ranges[1:]))
                if strategy == "full":
                    break
            query_scans = 0
            for key in expected:
                assert store.get(key) == expected[key]
                query_scans += store.last_query_reads
            live_bytes = sum(path.stat().st_size for path in store.files)
            retained_bytes = sum(path.stat().st_size for path in directory.glob("*.sst"))
            results[strategy] = dict(steps=steps, **totals, point_query_scans=query_scans,
                                     live_bytes=live_bytes, retained_bytes=retained_bytes, peak_sstable_bytes=peak_sstable_bytes,
                                     sstable_write_amplification=(flush_bytes + totals["merge_written_bytes"]) / logical_bytes)
            assert retained_bytes >= live_bytes
            if strategy == "leveled":
                assert len(steps) == 3
                # First two ranges are disjoint; third promotion overlaps L1.
                assert [step["input_files"] for step in steps] == [1, 1, 2]
                assert len([p for p in store.files if p.name.startswith("l1-")]) == 2
        print(json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    run()
```

```bash
uv run python -m labs.storage.lsm.check_v7
```

输出的 merge_read_bytes、merge_written_bytes 来自实际输入/输出文件大小；point_query_scans 来自真实 get。sstable_write_amplification 的分母是输入记录 JSON 编码字节，分子是 flush 与合并写入字节，不含 WAL、MANIFEST 和文件系统放大，因此只能在这个明确口径下比较。live_bytes 是 MANIFEST 活跃文件，retained_bytes 还含尚未回收的旧文件；peak_sstable_bytes 在每次输出发布后统计所有 SSTable，本版不删除旧文件，因此峰值等于最终保留量，不包含 WAL/MANIFEST/文件系统元数据。

不要预设 leveled 一定更省写或读：重复覆盖范围可能被多次重写，Bloom 也影响点查扫描数。本版冻结的是同一读取语义、真实两层选择和可复现计数；下一步若实现完整 leveled 引擎，还需多层容量、输出拆分、后台调度及读者安全回收。
