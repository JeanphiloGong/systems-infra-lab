from pathlib import Path

import pytest

from labs.storage.columnar.rows import Order
from labs.storage.columnar.columns import scan_columns, write_columns


def test_column_projection_does_not_open_unused_files(tmp_path: Path) -> None:
    write_columns(tmp_path, [Order(0, "east", 10, "a"), Order(1, None, 20, "b")])
    (tmp_path / "id.bin").unlink()
    (tmp_path / "note.bin").unlink()
    assert scan_columns(tmp_path, "east") == (10, 40, 4)
    assert scan_columns(tmp_path, None)[0] == 20


def test_misaligned_columns_rejected(tmp_path: Path) -> None:
    write_columns(tmp_path, [])
    assert scan_columns(tmp_path, "east") == (0, 0, 0)
    (tmp_path / "amount.bin").write_bytes(b"x")
    with pytest.raises(ValueError):
        scan_columns(tmp_path, "east")
