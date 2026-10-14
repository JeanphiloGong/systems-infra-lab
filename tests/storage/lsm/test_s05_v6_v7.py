from pathlib import Path

import pytest

from labs.storage.lsm.v6 import RecoveredStore
from labs.storage.lsm.v7 import compact_and_measure


def test_wal_recovery_and_bloom_negative(tmp_path: Path) -> None:
    store = RecoveredStore(tmp_path)
    store.put("k", "v")
    store.put("empty", "")
    assert store.get("missing") is None
    recovered = RecoveredStore(tmp_path)
    assert recovered.get("k") == "v"
    assert recovered.get("empty") == ""


def test_wal_rejects_bad_values(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        RecoveredStore(tmp_path).put("k", 3)  # type: ignore[arg-type]


def test_compaction_strategies_report_metrics(tmp_path: Path) -> None:
    first = RecoveredStore(tmp_path)
    first.put("a", "1")
    first.flush()
    second = RecoveredStore(tmp_path)
    second.put("a", "2")
    second.put("b", "2")
    second.flush()
    files = sorted(tmp_path.glob("*.sst"), key=lambda path: path.stat().st_mtime, reverse=True)
    full = compact_and_measure(files, tmp_path / "full.sst", "full")
    assert full.files_read == 2
    with pytest.raises(FileExistsError):
        compact_and_measure(files, tmp_path / "full.sst", "full")
    leveled = compact_and_measure(files, tmp_path / "level.sst", "leveled")
    assert leveled.files_read == 2
    assert full.bytes_written > 0 and leveled.peak_bytes >= leveled.bytes_read
