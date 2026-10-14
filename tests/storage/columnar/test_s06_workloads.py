from pathlib import Path
import pytest

from labs.storage.columnar.rows import Order, write_rows, scan_rows
from labs.storage.columnar.columns import write_columns, scan_columns
from labs.storage.columnar.workloads import point_row, point_columns, update_row, update_columns


def test_point_and_update_workloads_match(tmp_path: Path) -> None:
    orders = [Order(0, "east", 10, "a"), Order(1, "west", 20, "b")]
    path = tmp_path / "rows.bin"
    write_rows(path, orders)
    write_columns(tmp_path, orders)
    assert point_row(path, 1) == (orders[1], 56, 1)
    assert point_columns(tmp_path, 1) == (orders[1], 56, 4)
    replacement = Order(1, "east", 30, "changed")
    assert update_row(path, 1, replacement) == (56, 1)
    assert update_columns(tmp_path, 1, replacement) == (56, 4)
    assert point_row(path, 1)[0] == point_columns(tmp_path, 1)[0] == replacement
    assert scan_rows(path, "east")[0] == scan_columns(tmp_path, "east")[0] == 40


def test_invalid_update_does_not_modify_files(tmp_path: Path) -> None:
    path = tmp_path / "rows.bin"
    orders = [Order(0, "east", 10, "n")]
    write_rows(path, orders)
    write_columns(tmp_path, orders)
    before = {file.name: file.read_bytes() for file in tmp_path.iterdir()}
    with pytest.raises(ValueError):
        update_row(path, 0, Order(0, "east", -1, "n"))
    with pytest.raises(ValueError):
        update_columns(tmp_path, 0, Order(0, "east", -1, "n"))
    with pytest.raises(IndexError):
        update_columns(tmp_path, 1, orders[0])
    assert {file.name: file.read_bytes() for file in tmp_path.iterdir()} == before
