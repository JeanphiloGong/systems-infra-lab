# S01 v3：让连续与随机访问可以公平比较

前置 [v2](../v2/tutorial.md)。现在页读取正确了，接着有人问“连续访问比随机访问快多少”。如果两次实验访问不同订单、使用不同数据规模，再各打印一次总时间，数字无法回答这个问题。

本篇比较同一集合的两种排列，固定种子，记录每次查询的延迟分布。实验不清空 OS 页缓存，不声称测出磁盘随机访问性能。生成文件本身就可能把数据留在 OS 缓存；Python 的打开文件、解释器与调度开销也包含在计时里。

## 1. 只改变访问顺序

先从编号 0 到 31 的完整排列开始，复制后用局部 `random.Random(seed)` 洗牌。不能用有放回的随机抽样，否则有些订单读多次，有些完全没读。局部随机源不会改变其他代码的全局随机状态。

独立检查：

```python
import random

sequential = list(range(32))
shuffled = sequential.copy()
random.Random(17).shuffle(shuffled)
assert sorted(shuffled) == sequential
assert shuffled != sequential
```

固定种子保证相同 Python 随机实现下可复现顺序，不承诺所有未来 Python 版本的 shuffle 算法完全一致。此时输入已公平，但还只有一次计时的想法。

## 2. 报告分布以及能解释的计数

一次极慢请求会被平均值冲淡，因此测量每次 `get` 的耗时。排序后采用 nearest-rank 分位数：p95 是排序列表第 `ceil(n * .95)` 个，Python 索引减一。小样本 p95 很接近最大值，这是样本量决定的，不是统计错误。

`measure` 拒绝空请求列表与不存在编号，避免把无意义查询包装成正常性能结果。checksum 累加金额，方便比较实验，但不能代替逐记录正确性测试。请求数、页请求数、文件读取次数与字节数均报告本次调用的增量，因此将来同一 reader 预热后也能测量。不同页数从本次编号覆盖区间计算，不使用 reader 历史累计集合。

下面是完整三文件检查点。保留原两个文件，新增 `workload.py`；它没有自动执行入口，调用者负责数据规模、种子与结果输出。

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
from pathlib import Path

from labs.storage.pages.records import RECORD


class PageReader:
    def __init__(self, path: Path, page_size: int = 4096) -> None:
        if page_size < 1:
            raise ValueError("page_size must be positive")
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
        with self.path.open("rb") as source:
            source.seek(page_id * self.page_size)
            data = source.read(self.page_size)
        self.file_reads += 1
        self.bytes_read += len(data)
        expected = min(self.page_size, self.size - page_id * self.page_size)
        if len(data) != expected:
            raise ValueError("file changed during experiment")
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

运行同一数据集的两种访问顺序。每个 workload 创建新的 reader，所以应用计数独立；这不会清空 OS 缓存：

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
    assert sorted(shuffled) == sequential
    assert workloads(32, 17)[1] == shuffled
    for name, keys in (("sequential", sequential), ("random", shuffled)):
        report = measure(PageReader(path, 64), keys)
        assert report["requests"] == report["page_requests"] == report["file_reads"] == 32
        assert report["unique_pages"] == 4
        assert report["bytes_read"] == 2048
        assert report["checksum"] == 4960
        assert 0 <= report["p50_ns"] <= report["p95_ns"] <= report["max_ns"]
        print(name, report)
    try:
        measure(PageReader(path), [])
    except ValueError:
        pass
    else:
        raise AssertionError("empty workload accepted")
print("v3 ok")
PY
```

预期打印 sequential 与 random 两份字典，最后是 `v3 ok`。延迟数值每次不同，不应复制某次运行时间作为测试断言。两种顺序都是 32 次页读取、4 个不同页、2048 字节：64 字节页容纳 8 条记录，同一页被反复读取。没有应用缓存时，本实现并不会因为顺序访问自动合并请求。

尝试用 4096 字节页和 100000 条记录，交替执行两种顺序，多次报告分布，并记录 Python 版本、文件系统与机器环境。这个操作只是扩大实验，不足以隔离硬件效应。当前检查证明比较输入相同、查询计数可解释，没有证明哪种磁盘访问更快。

下一篇保留这套测量接口，加入容量有限的应用页缓存。访问顺序将开始影响可确定的缓存命中次数，而不必依赖不稳定的时间差判断局部性。
