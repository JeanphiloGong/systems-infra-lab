from __future__ import annotations

import argparse
import json
from pathlib import Path

from labs.storage.lsm.sstable import SSTable
from labs.storage.lsm.tombstones import TombstoneStore


def compact(files: list[Path], start: int, stop: int, output: Path) -> list[Path]:
    """Replace a contiguous newest-first slice; retain all input files on disk."""
    if not 0 <= start < stop <= len(files):
        raise ValueError("expected a nonempty in-bounds [start, stop) range")
    latest: dict[str, str | None] = {}
    for path in files[start:stop]:
        for key, encoded in SSTable(path).items():
            record = json.loads(encoded)
            if record == ["delete"]:
                value = None
            elif isinstance(record, list) and len(record) == 2 and record[0] == "value" and isinstance(record[1], str):
                value = record[1]
            else:
                raise ValueError("expected tagged value or delete record")
            if key not in latest:
                latest[key] = value
    if stop == len(files):
        latest = {key: value for key, value in latest.items() if value is not None}
    TombstoneStore.create(output, latest)
    return files[:start] + [output] + files[stop:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    old = args.directory / "old.sst"
    deleted = args.directory / "deleted.sst"
    new = args.directory / "new.sst"
    partial = args.directory / "partial.sst"
    full = args.directory / "full.sst"
    if args.create:
        TombstoneStore.create(old, {"k": "old", "keep": "old"})
        TombstoneStore.create(deleted, {"k": None})
        TombstoneStore.create(new, {"keep": "new"})
        after_partial = compact([new, deleted, old], 0, 2, partial)
        compact(after_partial, 0, 2, full)
    print("partial:", TombstoneStore([partial, old]).get("k"), SSTable(partial).get("k"))
    print("full:", TombstoneStore([full]).get("k"), SSTable(full).get("k"))
    print("keep:", TombstoneStore([full]).get("keep"))


if __name__ == "__main__":
    main()
