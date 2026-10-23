# S06 v1：只打开地区与金额列

前置 [v0](../v0/tutorial.md)。两行只需要地区和金额，却读了 112 字节。编号和备注占每行 36 字节，报表完全不用。若把字段放进独立文件，读取 region.bin 和 amount.bin 就能完成同一查询。

## 1. 行号成为列之间的连接关系

第 i 个地区必须对应第 i 个金额，不能分别排序两列。写入时先用 v0 的 encode 验证全部订单，解包后按原顺序分别写四个文件。每个字段的宽度不变；完整列文件总字节量仍与行文件相同，这里没有压缩。

目录须已存在，仅允许实验自己创建的目录。四个文件逐个覆盖，不是原子事务；并发读取或中途退出可能观察混合版本。本篇只在写入全部完成后扫描。

## 2. 投影减少的是读取量

scan_columns 只打开两列，检查长度为字段宽度整数倍且行数一致，然后逐个地区匹配并从相同行号取金额。它返回与 v0 同形状的 (sum,bytes,field_slots)。两行读取 (12+8)*2=40 字节、四个字段槽位；总金额仍应相同。

这仍然是 Python 标量循环，并没有获得 SIMD 或向量化执行。为突出布局，此版一次读入两个完整列，内存随数据量增长；批次处理在 v3 引入。

以下完整检查点保留 rows.py 的数据模型，新增 columns.py：

将下面的完整代码保存为 `labs/storage/columnar/rows.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/columnar/rows.py -->
```python
from dataclasses import dataclass
from pathlib import Path
from struct import Struct

ROW = Struct("<I12sQ32s")


@dataclass(frozen=True)
class Order:
    id: int
    region: str | None
    amount: int
    note: str


def pack_text(text: str | None, width: int) -> bytes:
    if text is None:
        return b"\0" * width
    encoded = text.encode("utf-8")
    if not encoded or b"\0" in encoded or len(encoded) > width:
        raise ValueError("text must be nonempty, NUL-free and fit field width")
    return encoded.ljust(width, b"\0")


def unpack_text(data: bytes) -> str | None:
    return data.rstrip(b"\0").decode("utf-8") or None


def encode(order: Order) -> bytes:
    if not 0 <= order.id < 2**32 or not 0 <= order.amount < 2**64:
        raise ValueError("integer outside field range")
    return ROW.pack(order.id, pack_text(order.region, 12), order.amount, pack_text(order.note, 32))


def write_rows(path: Path, orders: list[Order]) -> None:
    data = b"".join(encode(order) for order in orders)
    path.write_bytes(data)


def scan_rows(path: Path, region: str | None) -> tuple[int, int, int]:
    total = reads = fields = 0
    with path.open("rb") as source:
        while data := source.read(ROW.size):
            reads += len(data)
            if len(data) != ROW.size:
                raise ValueError("truncated row")
            _, stored, amount, _ = ROW.unpack(data)
            fields += 4
            if unpack_text(stored) == region:
                total += amount
    return total, reads, fields
```

将下面的完整代码保存为 `labs/storage/columnar/columns.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/columnar/columns.py -->
```python
from pathlib import Path
from struct import Struct

from labs.storage.columnar.rows import Order, ROW, encode, unpack_text

AMOUNT = Struct("<Q")
IDENTIFIER = Struct("<I")


def write_columns(directory: Path, orders: list[Order]) -> None:
    records = [ROW.unpack(encode(order)) for order in orders]
    (directory / "id.bin").write_bytes(b"".join(IDENTIFIER.pack(record[0]) for record in records))
    (directory / "region.bin").write_bytes(b"".join(record[1] for record in records))
    (directory / "amount.bin").write_bytes(b"".join(AMOUNT.pack(record[2]) for record in records))
    (directory / "note.bin").write_bytes(b"".join(record[3] for record in records))


def scan_columns(directory: Path, region: str | None) -> tuple[int, int, int]:
    regions = (directory / "region.bin").read_bytes()
    amounts = (directory / "amount.bin").read_bytes()
    if len(regions) % 12 or len(amounts) % AMOUNT.size or len(regions) // 12 != len(amounts) // AMOUNT.size:
        raise ValueError("column lengths disagree")
    count = len(amounts) // AMOUNT.size
    total = sum(AMOUNT.unpack_from(amounts, index * AMOUNT.size)[0]
                for index in range(count)
                if unpack_text(regions[index * 12:(index + 1) * 12]) == region)
    return total, len(regions) + len(amounts), count * 2
```

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.columnar.rows import Order, write_rows, scan_rows
from labs.storage.columnar.columns import write_columns, scan_columns

with TemporaryDirectory() as directory:
    root = Path(directory)
    orders = [Order(0, "east", 10, "a"), Order(1, None, 20, "b")]
    write_rows(root / "rows.bin", orders)
    write_columns(root, orders)
    assert scan_rows(root / "rows.bin", "east") == (10, 112, 8)
    assert scan_columns(root, "east") == (10, 40, 4)
    (root / "id.bin").unlink()
    (root / "note.bin").unlink()
    assert scan_columns(root, None) == (20, 40, 4)
    (root / "amount.bin").write_bytes(b"x")
    try:
        scan_columns(root, "east")
    except ValueError:
        pass
    else:
        raise AssertionError("misaligned columns accepted")
print("v1: same sum, 112 row bytes versus 40 projected bytes")
PY
```

删除不需要的列文件后查询仍成功，证明它没有偷偷读取编号或备注。预期输出 112 与 40 的比较。长度检查能发现部分损坏，不能识别两个同长度列来自不同数据版本，因此不可变一致快照是前提。

下一篇处理地区只有少数几个值却反复占用 12 字节的问题。
