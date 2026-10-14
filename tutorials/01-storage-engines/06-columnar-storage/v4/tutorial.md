# S06 v4：同一布局换负载：扫描、点查与更新

前置 v3。地区报表只读两列节省字节，但客服点开一条订单需要全部四列，修改整条订单也必须更新全部字段。这时列存是否仍然更合适，需要换成相同数据、相同结果的实验。

## 1. 点查用同一个已知行号

本版用slot定位，不构建主键索引；slot不是Order.id，不要求两者相等。行文件一次seek后读56字节；列布局在四个文件的slot*width处分别读取，总量也是56字节，却有四次文件读取。函数返回(Order,bytes,reads)，都不扫描之前的行。

负slot拒绝，越界或短读抛IndexError。None地区仍保留；备注按v0合同非空。没有测量打开文件耗时，也不把四次Python调用机械等同于四次磁盘寻道。

## 2. 完整行更新不能伪装成一个原子写入

update_row先编码整个Order，再定位写56字节。update_columns先校验输入与全部列的slot边界，再依次写4、12、8、32字节。返回(bytes_written,writes)。输入验证通过后仍可能遇到I/O错误，尤其四列更新会留下部分状态；即使行文件一次write也不保证断电原子。

为了避免让批次统计变旧，本实验只更新新的行/列副本，不更新v3已建统计的批次文件。更新批次需要重算并一致发布统计，留待未来事务模型。字典更新也可能改变编码范围，本篇不在旧字典上直接改码。

以下完整检查点继承rows.py和columns.py，新增workloads.py。点查与更新引入精确调用者，所以各函数不增加无用包装层。

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

<!-- checkpoint: labs/storage/columnar/workloads.py -->
```python
from pathlib import Path

from labs.storage.columnar.columns import AMOUNT, IDENTIFIER
from labs.storage.columnar.rows import Order, ROW, encode, unpack_text

FIELDS = (("id.bin", 4), ("region.bin", 12), ("amount.bin", 8), ("note.bin", 32))


def point_row(path: Path, slot: int) -> tuple[Order, int, int]:
    if slot < 0:
        raise ValueError("negative slot")
    with path.open("rb") as source:
        source.seek(slot * ROW.size)
        data = source.read(ROW.size)
    if len(data) != ROW.size:
        raise IndexError("slot outside file")
    identifier, region, amount, note = ROW.unpack(data)
    return Order(identifier, unpack_text(region), amount, unpack_text(note) or ""), len(data), 1


def point_columns(directory: Path, slot: int) -> tuple[Order, int, int]:
    if slot < 0:
        raise ValueError("negative slot")
    parts: list[bytes] = []
    for name, width in FIELDS:
        with (directory / name).open("rb") as source:
            source.seek(slot * width)
            data = source.read(width)
        if len(data) != width:
            raise IndexError("slot outside column")
        parts.append(data)
    return Order(IDENTIFIER.unpack(parts[0])[0], unpack_text(parts[1]),
                 AMOUNT.unpack(parts[2])[0], unpack_text(parts[3]) or ""), sum(map(len, parts)), 4


def update_row(path: Path, slot: int, order: Order) -> tuple[int, int]:
    data = encode(order)
    if slot < 0 or (slot + 1) * ROW.size > path.stat().st_size:
        raise IndexError("slot outside file")
    with path.open("r+b") as target:
        target.seek(slot * ROW.size)
        target.write(data)
    return len(data), 1


def update_columns(directory: Path, slot: int, order: Order) -> tuple[int, int]:
    data = encode(order)
    if slot < 0 or any((slot + 1) * width > (directory / name).stat().st_size for name, width in FIELDS):
        raise IndexError("slot outside columns")
    offset = 0
    for name, width in FIELDS:
        with (directory / name).open("r+b") as target:
            target.seek(slot * width)
            target.write(data[offset:offset + width])
        offset += width
    return len(data), 4
```

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.columnar.rows import Order, write_rows, scan_rows
from labs.storage.columnar.columns import write_columns, scan_columns
from labs.storage.columnar.workloads import point_row, point_columns, update_row, update_columns

with TemporaryDirectory() as directory:
    root = Path(directory)
    path = root / "rows.bin"
    orders = [Order(9, "east", 10, "a"), Order(7, "west", 20, "b")]
    write_rows(path, orders)
    write_columns(root, orders)
    row_scan = scan_rows(path, "east")
    column_scan = scan_columns(root, "east")
    assert row_scan == (10, 112, 8)
    assert column_scan == (10, 40, 4)
    assert point_row(path, 1) == (orders[1], 56, 1)
    assert point_columns(root, 1) == (orders[1], 56, 4)
    changed = Order(7, "east", 30, "changed")
    assert update_row(path, 1, changed) == (56, 1)
    assert update_columns(root, 1, changed) == (56, 4)
    assert point_row(path, 1)[0] == point_columns(root, 1)[0] == changed
    assert scan_rows(path, "east")[0] == scan_columns(root, "east")[0] == 40
    for function, location in ((point_row, path), (point_columns, root)):
        try:
            function(location, 99)
        except IndexError:
            pass
        else:
            raise AssertionError("out-of-range point read accepted")
print("scan bytes: row=112 column=40")
print("full point: row=56B/1 read column=56B/4 reads")
print("full update: row=56B/1 write column=56B/4 writes")
print("v4: all values and updated aggregate agree")
PY
```

这里投影扫描节省读取量，全行点查没有字节收益且增加文件操作；全行更新也是同样字节数、更多写入位置。这些结果针对本模型，不说明所有列存点查都慢。压缩、缓存、批次和执行引擎都可能改变真实数据库结果。

只修改amount一列时，两种布局都可以seek后写8字节，所以不能泛化为“列存更新一定写更多字节”。本篇选择完整行更新以展示跨文件一致性问题。整个系列没有实现Parquet、向量化执行、并发事务或WAL，列式布局本身不自动提供这些能力。
