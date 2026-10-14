from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from labs.storage.lsm.tombstones import TombstoneStore


def manifest_paths(directory: Path, names: object) -> list[Path]:
    if not isinstance(names, list):
        raise ValueError("manifest must be a list of filenames")
    paths: list[Path] = []
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".sst") or name in seen:
            raise ValueError("expected distinct direct-child .sst filenames")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("manifest file missing or not a regular local file")
        seen.add(name)
        paths.append(path)
    return paths


def publish(directory: Path, files: list[Path], crash: str | None = None) -> None:
    """Single writer on a local POSIX filesystem; input SSTables are immutable."""
    if crash not in {None, "before_publish", "after_publish"}:
        raise ValueError("unknown crash point")
    for path in files:
        if path.parent.resolve() != directory.resolve():
            raise ValueError("manifest files must be direct children")
    names = [path.name for path in files]
    paths = manifest_paths(directory, names)
    for path in paths:
        with path.open("rb") as source:
            os.fsync(source.fileno())
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
        temporary = directory / "MANIFEST.tmp"
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(names, stream)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            if crash == "before_publish":
                os._exit(71)
            os.replace(temporary, directory / "MANIFEST")
            if crash == "after_publish":
                os._exit(72)
            os.fsync(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        os.close(directory_fd)


def load(directory: Path) -> TombstoneStore:
    names = json.loads((directory / "MANIFEST").read_text(encoding="utf-8"))
    return TombstoneStore(manifest_paths(directory, names))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--create", action="store_true")
    actions.add_argument("--publish", action="store_true")
    parser.add_argument("--crash", choices=["before_publish", "after_publish"])
    args = parser.parse_args()
    if args.crash and not args.publish:
        parser.error("--crash requires --publish")
    old, new = args.directory / "old.sst", args.directory / "new.sst"
    if args.create:
        args.directory.mkdir(parents=True, exist_ok=True)
        TombstoneStore.create(old, {"k": "old", "stable": "yes"})
        TombstoneStore.create(new, {"k": "new"})
        publish(args.directory, [old])
    if args.publish:
        publish(args.directory, [new, old], args.crash)
    store = load(args.directory)
    print(json.dumps({"k": store.get("k"), "stable": store.get("stable")}))


if __name__ == "__main__":
    main()
