from pathlib import Path

import pytest

from labs.storage.columnar.rows import Order, scan_rows, write_rows


def test_rows_projection_counts(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_rows(path, [Order(0, "east", 10, "a"), Order(1, None, 20, "b")])
    assert scan_rows(path, "east") == (10, 112, 8)
    assert scan_rows(path, None)[0] == 20
    assert scan_rows(path, "missing")[0] == 0


def test_rows_empty_truncation_and_invalid(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_rows(path, [])
    assert scan_rows(path, "east") == (0, 0, 0)
    path.write_bytes(b"short")
    with pytest.raises(ValueError, match="truncated"):
        scan_rows(path, "east")
    with pytest.raises(ValueError):
        write_rows(path, [Order(0, "way-too-long-region", 10, "a")])
    with pytest.raises(ValueError):
        write_rows(path, [Order(0, "east", -1, "a")])
