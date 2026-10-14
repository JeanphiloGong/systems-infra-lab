from __future__ import annotations

from collections.abc import Iterable, Mapping
import argparse
import json
from pathlib import Path

from labs.storage.lsm.sstable import SSTable


class TombstoneStore:
    """Newest-first files whose values encode ['value', text] or ['delete']."""

    def __init__(self, files: Iterable[Path]) -> None:
        self._files = [SSTable(path) for path in files]

    @staticmethod
    def create(path: Path, entries: Mapping[str, str | None]) -> SSTable:
        encoded: dict[str, str] = {}
        for key, value in entries.items():
            if value is not None and not isinstance(value, str):
                raise TypeError("values must be strings or None for deletion")
            record = ["delete"] if value is None else ["value", value]
            encoded[key] = json.dumps(record, ensure_ascii=False)
        return SSTable.create(path, encoded)

    def get(self, key: str) -> str | None:
        for table in self._files:
            encoded = table.get(key)
            if encoded is None:
                continue
            record = json.loads(encoded)
            if record == ["delete"]:
                return None
            if isinstance(record, list) and len(record) == 2 and record[0] == "value" and isinstance(record[1], str):
                return record[1]
            raise ValueError("expected tagged value or delete record")
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    old, new = args.directory / "old.sst", args.directory / "new.sst"
    if args.create:
        TombstoneStore.create(old, {"k": "old", "keep": "yes"})
        TombstoneStore.create(new, {"k": None, "sentinel": "__TOMBSTONE__", "empty": "", "json": '["delete"]'})
    store = TombstoneStore([new, old])
    print([store.get(key) for key in ("k", "keep", "sentinel", "empty", "json", "missing")])


if __name__ == "__main__":
    main()
