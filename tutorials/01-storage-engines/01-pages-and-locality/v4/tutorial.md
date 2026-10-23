# S01 v4：缓存有容量，淘汰后也要读对

前置 [v3](../v3/tutorial.md)。32 条订单、64 字节一页，一共只有 4 个页；无缓存时却读取 32 次。页尺寸提供了空间局部性的机会，但只有保留已读页，后续相邻订单才可能复用它。

本篇添加只读应用缓存。文件从构造 reader 到实验结束都不可变；修改源文件后必须创建新 reader。没有脏页、写回、锁或崩溃恢复。容量以页计，保存的页面数据至多 `capacity * page_size` 字节，但 Python 字典、bytes 对象和统计集合也占内存，这不是进程内存上限。

## 1. 先看无限保留为什么不够

若直接把所有读取页放入字典，第二次查询能够命中，但扫描百万页后字典也有百万项。我们需要先规定容量，而非用“有缓存”替代内存预算。

设容量为 2，访问页序列是 0、1、0、2。第三次访问刷新页 0 的最近使用时间；读入页 2 时应淘汰页 1。之后再访问页 1，必须从文件重新加载且仍返回原值。这个轨迹确定了策略：Least Recently Used，淘汰最近最久未使用的页。

用 OrderedDict 表示从最旧到最新的顺序。命中时 `move_to_end`，缺失读入时插到末尾，满容量时先 `popitem(last=False)`。容量零明确表示关闭缓存，用于保留同一实验的无缓存对照，不是自动无限容量。

## 2. 将命中与文件读取分开计数

每个逻辑页请求都增加 `page_requests`，即使命中；只有真正调用读取才增加 `file_reads` 与 `bytes_read`。因此命中次数是两者之差。非法页号先拒绝，不污染计数。

完整检查点替换 `paged.py`，其余两个文件仍与 v3 相同。新增状态是容量和缓存，新增分支只有命中更新、缺失后按容量淘汰。读失败不会把不完整页放入缓存。

将下面的完整代码保存为 `labs/storage/pages/records.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/pages/records.py -->
```python
from pathlib import Path
from struct import Struct

RECORD = Struct("<II")


def write_records(path: Path, count: int) -> None:
    if not 0 <= count <= 429496730:
        raise ValueError("count out of range")
    with path.open("wb") as target:
        for key in range(count):
            target.write(RECORD.pack(key, key * 10))


def scan(path: Path, key: int) -> tuple[int | None, int]:
    consumed = 0
    with path.open("rb") as source:
        while data := source.read(RECORD.size):
            consumed += len(data)
            if len(data) != RECORD.size:
                raise ValueError("truncated record")
            stored_key, value = RECORD.unpack(data)
            if stored_key == key:
                return value, consumed
    return None, consumed


def direct(path: Path, key: int) -> tuple[int | None, int]:
    if key < 0:
        return None, 0
    with path.open("rb") as source:
        size = source.seek(0, 2)
        if size % RECORD.size:
            raise ValueError("truncated record")
        if key >= size // RECORD.size:
            return None, 0
        source.seek(key * RECORD.size)
        data = source.read(RECORD.size)
    if len(data) != RECORD.size:
        raise ValueError("truncated record")
    stored_key, value = RECORD.unpack(data)
    if stored_key != key:
        raise ValueError("key does not match slot")
    return value, len(data)
```

将下面的完整代码保存为 `labs/storage/pages/paged.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/pages/paged.py -->
```python
from collections import OrderedDict
from pathlib import Path

from labs.storage.pages.records import RECORD


class PageReader:
    def __init__(self, path: Path, page_size: int = 4096, capacity: int = 0) -> None:
        if page_size < 1:
            raise ValueError("page_size must be positive")
        if capacity < 0:
            raise ValueError("capacity must be nonnegative")
        self.capacity = capacity
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.path = path
        self.page_size = page_size
        self.size = path.stat().st_size
        if self.size % RECORD.size:
            raise ValueError("truncated record")
        self.bytes_read = 0
        self.page_requests = 0
        self.file_reads = 0
        self.pages_seen: set[int] = set()

    def read_page(self, page_id: int) -> bytes:
        if page_id < 0 or page_id * self.page_size >= self.size:
            raise ValueError("page outside file")
        self.page_requests += 1
        self.pages_seen.add(page_id)
        if page_id in self.cache:
            self.cache.move_to_end(page_id)
            return self.cache[page_id]
        with self.path.open("rb") as source:
            source.seek(page_id * self.page_size)
            data = source.read(self.page_size)
        self.file_reads += 1
        self.bytes_read += len(data)
        expected = min(self.page_size, self.size - page_id * self.page_size)
        if len(data) != expected:
            raise ValueError("file changed during experiment")
        if self.capacity:
            if len(self.cache) == self.capacity:
                self.cache.popitem(last=False)
            self.cache[page_id] = data
        return data

    def get(self, key: int) -> int | None:
        if key < 0 or key >= self.size // RECORD.size:
            return None
        start = key * RECORD.size
        stop = start + RECORD.size
        data = bytearray()
        for page_id in range(start // self.page_size, (stop - 1) // self.page_size + 1):
            page = self.read_page(page_id)
            base = page_id * self.page_size
            data.extend(page[max(start - base, 0):min(stop - base, len(page))])
        stored_key, value = RECORD.unpack(data)
        if stored_key != key:
            raise ValueError("key does not match slot")
        return value
```

将下面的完整代码保存为 `labs/storage/pages/workload.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/pages/workload.py -->
```python
import random
from math import ceil
from time import perf_counter_ns

from labs.storage.pages.paged import PageReader
from labs.storage.pages.records import RECORD


def workloads(count: int, seed: int) -> tuple[list[int], list[int]]:
    if count < 0:
        raise ValueError("count must be nonnegative")
    sequential = list(range(count))
    shuffled = sequential.copy()
    random.Random(seed).shuffle(shuffled)
    return sequential, shuffled


def measure(reader: PageReader, keys: list[int]) -> dict[str, int]:
    if not keys:
        raise ValueError("empty workload")
    before_requests = reader.page_requests
    before_reads = reader.file_reads
    before_bytes = reader.bytes_read
    pages: set[int] = set()
    durations: list[int] = []
    checksum = 0
    for key in keys:
        start = perf_counter_ns()
        value = reader.get(key)
        durations.append(perf_counter_ns() - start)
        if value is None:
            raise ValueError("workload requested missing record")
        checksum += value
        first = key * RECORD.size // reader.page_size
        last = ((key + 1) * RECORD.size - 1) // reader.page_size
        pages.update(range(first, last + 1))
    durations.sort()
    return {
        "requests": len(keys),
        "checksum": checksum,
        "page_requests": reader.page_requests - before_requests,
        "file_reads": reader.file_reads - before_reads,
        "bytes_read": reader.bytes_read - before_bytes,
        "unique_pages": len(pages),
        "p50_ns": durations[ceil(len(durations) * 0.50) - 1],
        "p95_ns": durations[ceil(len(durations) * 0.95) - 1],
        "max_ns": durations[-1],
    }
```

运行以下独立实验：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.pages.records import write_records
from labs.storage.pages.paged import PageReader
from labs.storage.pages.workload import measure, workloads

with TemporaryDirectory() as directory:
    path = Path(directory) / "orders.bin"
    write_records(path, 32)
    sequential, shuffled = workloads(32, 17)
    reader = PageReader(path, 64, capacity=4)
    cold = measure(reader, sequential)
    warm = measure(reader, shuffled)
    assert cold["file_reads"] == 4
    assert cold["bytes_read"] == 256
    assert warm["file_reads"] == warm["bytes_read"] == 0
    assert warm["page_requests"] == 32
    assert cold["checksum"] == warm["checksum"] == 4960
    print("application cold", cold)
    print("application warm", warm)
    one_page_seq = measure(PageReader(path, 64, 1), sequential)
    one_page_random = measure(PageReader(path, 64, 1), shuffled)
    assert one_page_seq["file_reads"] == 4
    assert one_page_random["file_reads"] > 4
    assert one_page_seq["checksum"] == one_page_random["checksum"]
    reader = PageReader(path, 8, capacity=2)
    for key in (0, 1, 0, 2):
        assert reader.get(key) == key * 10
        assert len(reader.cache) <= 2
    assert list(reader.cache) == [0, 2]
    assert reader.file_reads == 3
    assert reader.get(1) == 10
    assert reader.file_reads == 4
    assert list(reader.cache) == [2, 1]
    crossing = PageReader(path, 3, capacity=1)
    assert crossing.get(1) == 10
    assert len(crossing.cache) == 1
    try:
        PageReader(path, capacity=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative capacity accepted")
print("v4 ok")
PY
```

预期打印两份指标和 `v4 ok`。第一次应用冷缓存读取 4 页共 256 字节；第二次应用暖缓存读取零字节，但仍请求 32 页。因为全部 4 页都放得下，第二次即使乱序也全部命中。

容量缩到 1 后，连续顺序依然只需要 4 次加载，固定乱序会需要更多。局部性的收益来自下一次访问落在仍驻留的页，而不仅仅是“数组连续”。工作集超过容量后会重新加载；淘汰不是丢失数据，因为原始文件仍保存所有记录。

注意“应用冷缓存”只指新建 reader 的字典为空。操作系统很可能已缓存刚写过的文件，Python 也有文件缓冲；这里没有测出冷磁盘读取。暖缓存更少的应用读取次数可以确定，延迟变快多少需要在说明环境后单独测量。

## 完成这个模块后

可选执行 [参考分支检查](../../../../docs/reference-checks.md) 检查最终代码。正文旧版本通过 [参考分支检查](../../../../docs/reference-checks.md) 在临时目录提取完整文件并执行各篇打印的检查；不会覆盖你的工作目录。

你现在可以从相同记录出发解释扫描成本、直接定位假设、跨页放大、相同集合的不同排列和 LRU 淘汰。这个缓存仍不是生产数据库缓冲池：它没有更新一致性、并发访问、脏页或 pin/unpin；下一模块学习 B+Tree 时可以使用这里的页模型，但需要另行定义节点布局。

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/storage/pages/ -q
uv run python tests/storage/pages/replay_s01.py
```

</details>
