# S06 v0：报表只需两列，行文件却读了四列

客服需要东区订单总金额。每条订单同时包含编号、地区、金额、备注，但这个查询只需要地区和金额。本篇先写一个结果正确的行式扫描器，再统计为了这两列实际读取了多少字节。

假设输入为小型不可变订单文件，无并发写入。每行使用 4 字节无符号编号、12 字节地区、8 字节无符号金额、32 字节备注，总共 56 字节。地区允许 None，编码为全零；非缺失文本不能空、含 NUL 或超过对应 UTF-8 字节宽度。备注为非空文本，金额非负。这个格式不是通用数据库类型系统。

## 1. 先让读写共享一个明确布局

若用可变宽文本，无法从文件长度直接解释每行成本。Struct("<I12sQ32s") 明确小端和字段宽度，不使用原生对齐。write_rows 先验证并编码所有行，再覆盖目标文件，因此输入校验失败不会先截断旧文件；但中途 I/O 故障仍可能留下不完整文件。

Order 只是四个字段的不可变记录。pack_text/unpack_text 管理 UTF-8 填充与缺失值，encode 统一验证整数范围。扫描读取一整行，用 region 过滤，匹配就把金额加进 Python 整数总和。

## 2. 同时返回结果和代价

scan_rows 返回 (总金额,应用读到字节数,布局中扫描字段数)。字段数每行加四，指读入的字段槽位数，不是四次文件读取或四次 CPU 解码。实际只对地区做文本解码，编号和备注仍随行字节一起读入。找到匹配行也必须继续扫描后面的订单，不能像点查提前结束。

以下新建 labs/storage/columnar/rows.py，构成完整检查点：

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

运行首尾、缺失、空文件和截断检查：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.columnar.rows import Order, scan_rows, write_rows

with TemporaryDirectory() as directory:
    path = Path(directory) / "orders.bin"
    orders = [Order(0, "east", 10, "a"), Order(1, None, 20, "b")]
    write_rows(path, orders)
    assert scan_rows(path, "east") == (10, 112, 8)
    assert scan_rows(path, None) == (20, 112, 8)
    assert scan_rows(path, "missing") == (0, 112, 8)
    write_rows(path, [])
    assert scan_rows(path, "east") == (0, 0, 0)
    path.write_bytes(b"broken")
    try:
        scan_rows(path, "east")
    except ValueError:
        pass
    else:
        raise AssertionError("partial row accepted")
print("v0: two rows read 112 bytes and 8 field slots")
PY
```

预期最后一行成功信息。即使找不到地区，也读了同样的 112 字节。Python 缓冲、文件系统和 OS 缓存决定更底层的读取，本文没有清缓存或测设备带宽。

下一篇保持 56 字节的逻辑字段格式，但把同一字段连续存放；查询将能完全不打开编号和备注文件。
