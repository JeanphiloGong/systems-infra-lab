# S06 v3：批次统计：不相交才允许跳过

前置 v2。八条金额为0、10、20、30、40、50、60、70的订单，每两行为一批。查询金额[20,30]时只有第二批可能匹配。如果仍打开所有批次，列投影虽减少字段，却没有减少被扫描的行组。

## 1. 写入时把数据和统计绑定

write_batches按原顺序切组，每组写v1的四个列文件，同时从同一组Order计算count、minimum、maximum。Batch是不可变描述对象，返回tuple；空输入没有批次，batch_size必须为正。每个batch目录只能新建，避免悄悄覆盖原统计对应文件。

本版统计留在内存，不是可重开元数据格式。调用者必须使用write_batches返回的Batch，不能伪造min/max或在写完后修改文件。长度检查只能发现尺寸变化，不能发现同长度的内容替换。保证无漏读依赖统计与不可变数据来自同一次构建；不为损坏统计提供恢复能力。

## 2. 闭区间边界不能错过

仅当maximum<low或minimum>high时跳过；等号必须读取。统计范围与查询重叠只是必要条件，例如[0,100]批次不一定有[40,60]中的记录，读取后仍需逐行核对金额和地区。

返回(sum,bytes_read,batches_read)。读取量仅计打开的region和amount列，不包括构建阶段写入，也不把缓存当实际磁盘。空范围low>high不读数据。批次中地区缺失继续使用v0的None语义。

以下完整检查点包含rows.py、columns.py和新增batches.py。v2字典算法已独立验证，本篇有意使用固定宽地区，以便直接计算每批读取字节。

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

将下面的完整代码保存为 `labs/storage/columnar/batches.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/columnar/batches.py -->
```python
from dataclasses import dataclass
from pathlib import Path

from labs.storage.columnar.columns import AMOUNT, write_columns
from labs.storage.columnar.rows import Order, unpack_text


@dataclass(frozen=True)
class Batch:
    directory: Path
    count: int
    minimum: int
    maximum: int


def write_batches(directory: Path, orders: list[Order], batch_size: int) -> tuple[Batch, ...]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    batches: list[Batch] = []
    for start in range(0, len(orders), batch_size):
        group = orders[start:start + batch_size]
        target = directory / f"batch-{start}"
        target.mkdir()
        write_columns(target, group)
        batches.append(Batch(target, len(group), min(order.amount for order in group), max(order.amount for order in group)))
    return tuple(batches)


def scan_batches(batches: tuple[Batch, ...], region: str | None, low: int, high: int) -> tuple[int, int, int]:
    total = bytes_read = batches_read = 0
    if low > high:
        return total, bytes_read, batches_read
    for batch in batches:
        if batch.maximum < low or batch.minimum > high:
            continue
        regions = (batch.directory / "region.bin").read_bytes()
        amounts = (batch.directory / "amount.bin").read_bytes()
        if len(regions) != batch.count * 12 or len(amounts) != batch.count * AMOUNT.size:
            raise ValueError("batch data changed")
        bytes_read += len(regions) + len(amounts)
        batches_read += 1
        for index in range(batch.count):
            amount = AMOUNT.unpack_from(amounts, index * AMOUNT.size)[0]
            if low <= amount <= high and unpack_text(regions[index * 12:(index + 1) * 12]) == region:
                total += amount
    return total, bytes_read, batches_read
```

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.columnar.rows import Order
from labs.storage.columnar.batches import write_batches, scan_batches

with TemporaryDirectory() as directory:
    root = Path(directory)
    orders = [Order(i, "east", i * 10, "n") for i in range(8)]
    batches = write_batches(root, orders, 2)
    assert scan_batches(batches, "east", 20, 30) == (50, 40, 1)
    assert scan_batches(batches, "east", 31, 39) == (0, 0, 0)
    assert scan_batches(batches, "east", 0, 70) == (280, 160, 4)
    assert scan_batches(batches, "east", 40, 30) == (0, 0, 0)
    for low in range(-1, 72):
        for high in (low, low + 10, 100):
            expected = sum(order.amount for order in orders if low <= order.amount <= high)
            assert scan_batches(batches, "east", low, high)[0] == expected
    overlap = root / "overlap"
    overlap.mkdir()
    groups = write_batches(overlap, [Order(0, None, 0, "n"), Order(1, "east", 100, "n")], 2)
    assert scan_batches(groups, "east", 40, 60) == (0, 40, 1)
print("v3: one selected batch=40 bytes; full scan=160 bytes; gap=0 bytes")
PY
```

打印的40与160可由每行12+8字节、每批两行推导，断言还遍历多个边界与逐行参考求和比较。数据若乱序分散，每批min/max可能很宽，结果仍正确但少有批次可跳过；统计没有承诺总能省读取。

下一篇使用同一组订单比较完整行点查和完整行更新，观察列布局的代价，而不把这个报表优势推及全部负载。
