# S01 v0：查一条订单到底读了多少字节

订单导出文件里有一百万条记录。客服输入最后一条订单的编号，程序虽然只返回一个金额，却可能从文件开头读到结尾。本篇先实现正确的扫描，再把这个成本显露出来；不急着引入索引或缓存。

你需要 Python 3.12 和基本文件读写知识。在仓库根目录执行 `uv sync --group dev`。实验只创建临时文件，不需要数据库。我们把完整订单压缩成编号与金额两个整数，并假设编号从零连续排列、金额为编号乘十。真实订单可能变长、删除或乱序，这些情况不属于本格式。

## 1. 先规定能被重复读取的文件格式

三个订单 `(0,0)、(1,10)、(2,20)` 应占多少空间？文本中的 `20` 与 `0` 长度不同，无法直接约定下一条记录的位置。我们先选固定宽度：两个 32 位无符号整数，共 8 字节。

下面是独立演示，不是需要添加到最终文件的补丁：

```python
from struct import Struct

record = Struct("<II")
data = record.pack(2, 20)
assert len(data) == 8
assert record.unpack(data) == (2, 20)
```

`<` 明确使用小端；两个 `I` 分别编码编号和金额，不能存负数。这样同一文件在不同机器上不会因为原生对齐规则改变记录宽度。现在我们能够读一条记录，但还没有按编号查找的程序。

## 2. 扫描时把每次读取的成本带回来

寻找编号 2，要依次看 0、1、2。只返回金额会掩盖这三次读取，因此查询返回 `(金额或 None, 已读取字节数)`。找不到不是损坏，返回 None；只读到半条记录却是文件损坏，抛出 `ValueError`。本实现按需发现截断，并不会在找到前面的记录后继续检查整个文件。

生成器负责写入教学数据，会覆盖指定文件。`count` 的上限保证最大金额仍能装入 32 位整数：`(count - 1) * 10 <= 2**32 - 1`。路径不存在或无法打开时，让原始 `OSError` 传播给调用者。

新建 `labs/storage/pages/records.py`。下面是本版本的完整检查点，包含生成数据和扫描，不需要拼接前面的演示：

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
```

`while data := ...` 每次读最多 8 字节，空字节串表示 EOF。先累计长度再解码，因此不会假装尾部残片是一条正常记录。`with` 在返回与异常时都会关闭文件。类型注解描述约定，不会在运行时自动把字符串编号转成整数。

运行这个检查；成功时只输出 `v0 ok`：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.pages.records import scan, write_records

with TemporaryDirectory() as directory:
    path = Path(directory) / "orders.bin"
    write_records(path, 3)
    assert path.stat().st_size == 24
    assert scan(path, 0) == (0, 8)
    assert scan(path, 2) == (20, 24)
    assert scan(path, 3) == (None, 24)
    write_records(path, 0)
    assert scan(path, 0) == (None, 0)
    path.write_bytes(b"bad")
    try:
        scan(path, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("truncation was accepted")
    path.unlink()
    try:
        scan(path, 0)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing file was accepted")
print("v0 ok")
PY
```

这组检查分别覆盖首条、末条、缺失编号、空文件、截断文件与路径不存在。读取量是 Python `read()` 返回给应用的字节数。Python 缓冲、操作系统预读和页缓存可能让底层实际读取量不同，所以这里没有测量磁盘 I/O。

现在有了正确且可观察的扫描基线。把记录数改为一百万，再查询最后一个编号，读取量会成为八百万字节。下一篇利用固定宽度和连续编号直接定位，消除这个随记录位置增长的扫描成本。
