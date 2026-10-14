from pathlib import Path


def query_files(paths: list[Path], key: str) -> tuple[str | None, int]:
    reads = 0
    for path in paths:
        reads += 1
        for line in path.read_text().splitlines():
            stored_key, value = line.split("\t", 1)
            if stored_key == key:
                return value, reads
    return None, reads
