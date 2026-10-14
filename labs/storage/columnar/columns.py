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
