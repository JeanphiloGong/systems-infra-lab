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
