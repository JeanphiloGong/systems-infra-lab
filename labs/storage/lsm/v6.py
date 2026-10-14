from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from labs.storage.bloom.table import ImmutableTable
from labs.storage.lsm.manifest import load, publish
from labs.storage.lsm.tombstones import TombstoneStore
from labs.storage.lsm.wal import WAL


class RecoveredStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        if not (directory / "MANIFEST").exists():
            if any(directory.iterdir()):
                raise ValueError("nonempty directory has no MANIFEST")
            publish(directory, [])
        self.wal = WAL(directory / "write.wal")
        if not self.wal.path.exists():
            self.wal.clear()
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        self.files = [table.path for table in load(directory)._files]
        self.tables = [ImmutableTable(path) for path in self.files]
        self.values: dict[str, str | None] = {}
        for key, value in self.wal.replay():
            self.values[key] = value
        self.failed = False
        self.last_query_reads = 0

    def put(self, key: str, value: str | None) -> None:
        if self.failed:
            raise RuntimeError("reopen store after a write failure")
        if not isinstance(key, str) or (value is not None and not isinstance(value, str)):
            raise TypeError("key/value must be strings; None means delete")
        try:
            self.wal.append(key, value)
        except Exception:
            self.failed = True
            raise
        self.values[key] = value

    def get(self, key: str) -> str | None:
        self.last_query_reads = 0
        if key in self.values:
            return self.values[key]
        for table in self.tables:
            encoded, reads = table.query(key)
            self.last_query_reads += reads
            if encoded is None:
                continue
            record = json.loads(encoded)
            if record == ["delete"]:
                return None
            if isinstance(record, list) and len(record) == 2 and record[0] == "value" and isinstance(record[1], str):
                return record[1]
            raise ValueError("invalid tagged record")
        return None

    def flush(self, crash: str | None = None) -> Path | None:
        if crash not in {None, "before_publish", "after_publish", "after_wal_clear"}:
            raise ValueError("unknown crash point")
        if self.failed:
            raise RuntimeError("reopen store after a write failure")
        if not self.values:
            return None
        try:
            path = self.directory / (uuid4().hex + ".sst")
            TombstoneStore.create(path, self.values)
            if crash == "before_publish":
                os._exit(81)
            publish(self.directory, [path] + self.files)
            if crash == "after_publish":
                os._exit(82)
            self.wal.clear()
            if crash == "after_wal_clear":
                os._exit(83)
            self.files.insert(0, path)
            self.tables.insert(0, ImmutableTable(path))
            self.values.clear()
            return path
        except Exception:
            self.failed = True
            raise
