from __future__ import annotations

import argparse
from pathlib import Path
from collections.abc import Iterable

from labs.storage.lsm.sstable import SSTable


class VersionedStore:
    """Newest-to-oldest immutable files; caller supplies priority order."""

    def __init__(self, files: Iterable[Path]) -> None:
        self._files = [SSTable(path) for path in files]

    def get(self, key: str) -> str | None:
        for table in self._files:
            value = table.get(key)
            if value is not None:
                return value
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    old, new = args.directory / "old.sst", args.directory / "new.sst"
    if args.create:
        SSTable.create(old, {"k": "old", "keep": "yes", "empty": "old"})
        SSTable.create(new, {"k": "new", "empty": ""})
    store = VersionedStore([new, old])
    print([store.get(key) for key in ("k", "keep", "empty", "missing")])


if __name__ == "__main__":
    main()
