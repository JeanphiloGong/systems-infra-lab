from pathlib import Path

import pytest

from labs.storage.pages.records import direct, scan, write_records


def test_scan_first_last_missing_and_byte_cost(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 4)
    assert scan(path, 0) == (0, 8)
    assert scan(path, 3) == (30, 32)
    assert scan(path, 4) == (None, 32)


def test_scan_empty_and_truncated(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 0)
    assert scan(path, 0) == (None, 0)
    path.write_bytes(b"broken")
    with pytest.raises(ValueError, match="truncated"):
        scan(path, 0)


def test_direct_matches_scan_without_position_cost(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 100)
    for key in range(100):
        assert direct(path, key) == (scan(path, key)[0], 8)
    assert direct(path, -1) == (None, 0)
    assert direct(path, 100) == (None, 0)


def test_direct_rejects_truncation_and_wrong_slot(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    path.write_bytes(b"short")
    with pytest.raises(ValueError, match="truncated"):
        direct(path, 0)
    write_records(path, 2)
    path.write_bytes(path.read_bytes()[8:] + path.read_bytes()[:8])
    with pytest.raises(ValueError, match="slot"):
        direct(path, 0)
