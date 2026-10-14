# S01 v1：利用固定记录宽度直接定位

前置是 [v0](../v0/tutorial.md)。最后一条订单只需返回 8 字节，扫描却把前面所有订单读了一遍。用三条记录复现：`scan(path, 2)` 返回 `(20, 24)`。这不是解码慢，而是查找路径经过了不需要的记录。

## 1. 从编号算出位置

本文件的编号恰好等于从零开始的槽位，记录宽度恒为 8；因此编号 2 位于偏移 16。若只是金额字段长度固定、编号却可以乱序，这个公式便不成立。这里没有建立通用索引，连续编号是输入格式的一部分。

`source.seek(key * RECORD.size)` 移动当前位置，下一次 `read(8)` 就读取目标记录。先 `seek(0, 2)` 得到文件长度；这不向应用返回文件内容，不计入读取字节。长度必须是记录宽度的整数倍，否则全文件格式已经损坏。负数和超过槽位数的编号返回 `(None, 0)`。

计算后仍核对记录中的编号：一旦文件被乱序重写，不能把错误金额当成查询成功。实验期间文件不可变；长度检查并不是对并发改写的锁定。

## 2. 保留扫描作对照，形成完整检查点

替换 `labs/storage/pages/records.py` 为以下完整文件。只增加 `direct`；生成器和扫描含义与 v0 相同。新函数无缓存，无持久化索引，也不改变文件。

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

运行以下检查，首尾查询都应只向应用返回 8 字节，扫描仍返回随位置增长的字节数：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.pages.records import direct, scan, write_records

with TemporaryDirectory() as directory:
    path = Path(directory) / "orders.bin"
    write_records(path, 3)
    assert direct(path, 0) == (0, 8)
    assert direct(path, 2) == (20, 8)
    assert scan(path, 2) == (20, 24)
    assert direct(path, -1) == (None, 0)
    assert direct(path, 3) == (None, 0)
    data = path.read_bytes()
    path.write_bytes(data[8:16] + data[:8] + data[16:])
    try:
        direct(path, 0)
    except ValueError as error:
        assert "slot" in str(error)
    else:
        raise AssertionError("wrong slot accepted")
    path.write_bytes(b"short")
    try:
        direct(path, 0)
    except ValueError as error:
        assert "truncated" in str(error)
    else:
        raise AssertionError("truncation accepted")
print("v1 ok")
PY
```

预期输出 `v1 ok`。首尾与越界证明定位合同，打乱槽位证明格式限制，残片证明不静默接受损坏。这里报告应用数据读取量，不包括文件打开、定位或元数据成本；更不能声称硬盘只读了 8 字节。

现在查询不再随记录位置扫描。下一篇把读取单位改成页，观察记录跨页时为什么不能只读起始页。
