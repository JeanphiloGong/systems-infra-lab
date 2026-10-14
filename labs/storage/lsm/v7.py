from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .compaction import compact
from .tombstones import TombstoneStore


@dataclass(frozen=True)
class CompactionMetrics:
    logical_records_read: int
    logical_records_written: int
    bytes_read: int
    bytes_written: int
    peak_bytes: int
    files_read: int


def measure(files: list[Path]) -> tuple[int, int]:
    return sum(path.stat().st_size for path in files), sum(1 for _ in TombstoneStore(files)._files)


def compact_and_measure(files: list[Path], output: Path, strategy: str) -> CompactionMetrics:
    if strategy not in {"full", "leveled"}:
        raise ValueError("strategy must be full or leveled")
    selected = files if strategy == "full" else files[-2:]
    before_bytes, _ = measure(selected)
    before_records = sum(sum(1 for _ in table.items()) for table in TombstoneStore(selected)._files)
    replacement = compact(files, len(files) - len(selected), len(files), output)
    after_bytes = output.stat().st_size
    after_records = sum(1 for _ in TombstoneStore([output])._files[0].items())
    return CompactionMetrics(before_records, after_records, before_bytes, after_bytes, before_bytes + after_bytes, len(selected))
