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
