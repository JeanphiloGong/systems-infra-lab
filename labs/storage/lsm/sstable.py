from __future__ import annotations

from collections.abc import Iterator, Mapping
import json
import os
from pathlib import Path
import tempfile


class SSTable:
    """Immutable sorted JSONL file; point reads scan all records in this version."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def create(cls, path: Path, entries: Mapping[str, str]) -> SSTable:
        records = list(entries.items())
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in records):
            raise TypeError("keys and values must be strings")
        records.sort()
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as target:
            temporary = Path(target.name)
            try:
                for key, value in records:
                    target.write(json.dumps([key, value], ensure_ascii=False) + "\n")
                target.flush()
                os.link(temporary, path)
            finally:
                temporary.unlink()
        return cls(path)

    def items(self) -> Iterator[tuple[str, str]]:
        previous: str | None = None
        with self.path.open(encoding="utf-8") as source:
            for line in source:
                record = json.loads(line)
                if not isinstance(record, list) or len(record) != 2 or not all(isinstance(value, str) for value in record):
                    raise ValueError("expected [string key, string value]")
                key, value = record
                if previous is not None and key <= previous:
                    raise ValueError("keys must be strictly increasing")
                previous = key
                yield key, value

    def get(self, key: str) -> str | None:
        found: str | None = None
        for stored, value in self.items():
            if stored == key:
                found = value
        return found


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    if args.create:
        SSTable.create(args.path, {"z": "latest", "a": "first"})
    print(list(SSTable(args.path).items()))


if __name__ == "__main__":
    main()
