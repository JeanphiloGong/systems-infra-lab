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
