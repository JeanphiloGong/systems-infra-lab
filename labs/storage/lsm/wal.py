from __future__ import annotations

import os
from pathlib import Path

from labs.storage.wal.framing import decode, encode


class WAL:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, key: str, value: str | None) -> None:
        if not isinstance(key, str) or (value is not None and not isinstance(value, str)):
            raise TypeError("invalid WAL record")
        with self.path.open("ab") as stream:
            stream.write(encode({"key": key, "value": value}))
            stream.flush()
            os.fsync(stream.fileno())

    def replay(self) -> list[tuple[str, str | None]]:
        if not self.path.exists():
            return []
        frames, valid_end, torn = decode(self.path.read_bytes())
        records: list[tuple[str, str | None]] = []
        for record in frames:
            if set(record) != {"key", "value"} or not isinstance(record["key"], str) or (record["value"] is not None and not isinstance(record["value"], str)):
                raise ValueError("invalid WAL record")
            records.append((record["key"], record["value"]))
        if torn:
            with self.path.open("r+b") as stream:
                stream.truncate(valid_end)
                stream.flush()
                os.fsync(stream.fileno())
        return records

    def clear(self) -> None:
        with self.path.open("wb") as stream:
            stream.flush()
            os.fsync(stream.fileno())
