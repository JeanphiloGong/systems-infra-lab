# S01 v2：读取一条跨页记录

前置 [v1](../v1/tutorial.md)。订单 1 的字节区间是 [8,16)。若一次读取单位为 10 字节，起始页只有区间 [0,10)，还差后面 6 字节。仅仅读取起始页再切出 8 字节会失败。这次用刻意很小的页让边界看得见，真实数据库页通常大得多。

本篇仍只读取不可变文件，编号等于槽位。页只是文件中固定大小的连续区间；最后一页允许短于页长，但文件长度必须是完整记录宽度的倍数。我们不模拟操作系统分页，也不声明一次应用页读取对应一次设备 I/O。

## 1. 先把跨界算清楚

记录范围使用左闭右开的 [start, stop)。起始页编号是 `start // page_size`；最后一个实际字节是 `stop - 1`，所以末页编号是 `(stop - 1) // page_size`。不能用 `stop // page_size`，否则恰好落在页边界的记录会多读一页。

这个独立演示先验证边界公式：

```python
assert list(range(8 // 10, (16 - 1) // 10 + 1)) == [0, 1]
assert list(range(0 // 8, (8 - 1) // 8 + 1)) == [0]
```

对每一页只拼接与记录相交的部分。页面在文件中的起点为 base，则切片从 `max(start-base, 0)` 开始，到 `min(stop-base, len(page))` 结束。页可能比记录还小，因此循环不假定最多跨两页。

## 2. 让查询共享页尺寸与统计

连续查几条记录时，调用者需要累计页请求数、不同页集合、读取字节数。为此新增 `PageReader`，保存一份文件路径、已知长度与计数器；构造时只检查长度，不读取数据。对象并不持有长期打开的文件，页读取各自用 `with` 关闭文件，因此本版时延还包含打开文件的开销。

`get` 接收编号并返回金额或 None；`read_page` 接收有效页号并返回原始字节。每次页请求增加 `page_requests`，实际读取增加 `file_reads` 与 `bytes_read`，`pages_seen` 去重。目前没有缓存，因此两个次数相同，下一阶段它们将有不同含义。读取长度检查能发现部分文件缩短，但不能防止同长度内容被并发修改；不可变文件仍是前提。

本次完整检查点包含两个文件。第一个保留 v1，第二个新增页读取与跨页拼接；下面没有隐藏依赖。

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

运行检查：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.pages.records import direct, write_records
from labs.storage.pages.paged import PageReader

with TemporaryDirectory() as directory:
    path = Path(directory) / "orders.bin"
    write_records(path, 3)
    reader = PageReader(path, 10)
    assert reader.get(1) == 10
    assert (reader.page_requests, reader.bytes_read) == (2, 20)
    assert direct(path, 1) == (10, 8)
    assert reader.get(2) == 20
    assert (reader.page_requests, reader.bytes_read) == (4, 34)
    assert reader.pages_seen == {0, 1, 2}
    assert reader.get(3) is None
    assert reader.page_requests == 4
    for size in (1, 7, 8, 10, 16, 4096):
        assert [PageReader(path, size).get(k) for k in range(3)] == [0, 10, 20]
    try:
        PageReader(path, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("zero page size accepted")
    path.write_bytes(b"bad")
    try:
        PageReader(path, 10)
    except ValueError:
        pass
    else:
        raise AssertionError("partial record accepted")
print("v2 ok")
PY
```

预期 `v2 ok`。查编号 1 读了两个完整 10 字节页，总计 20 字节，虽然只需要 8 字节。再查编号 2，读 10 字节的页 1 和 4 字节的尾页 2，累计 34 字节。不同页只有三个，但页请求四次：页 1 被重复读取。最后一页短并不等于最后一条记录被截断。

现在不同页尺寸都能返回相同记录，且额外读取量可解释。下一篇固定数据与访问顺序，把单次观察扩展成可复现的工作负载；暂时不要从两次计时判断随机读取快慢。
