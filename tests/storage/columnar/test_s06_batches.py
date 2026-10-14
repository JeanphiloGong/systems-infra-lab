from pathlib import Path
import pytest

from labs.storage.columnar.batches import write_batches, scan_batches
from labs.storage.columnar.rows import Order


def test_closed_boundaries_and_skip_counts(tmp_path: Path) -> None:
    batches = write_batches(tmp_path, [Order(i, "east", i * 10, "n") for i in range(8)], 2)
    assert scan_batches(batches, "east", 20, 30) == (50, 40, 1)
    assert scan_batches(batches, "east", 31, 39) == (0, 0, 0)
    assert scan_batches(batches, "east", 0, 70) == (280, 160, 4)
    assert scan_batches(batches, "east", 40, 30) == (0, 0, 0)


def test_overlapping_minmax_is_not_proof_of_matching_row(tmp_path: Path) -> None:
    batches = write_batches(tmp_path, [Order(0, None, 0, "n"), Order(1, "east", 100, "n")], 2)
    assert scan_batches(batches, "east", 40, 60) == (0, 40, 1)
    assert scan_batches(batches, None, 0, 0) == (0, 40, 1)


def test_empty_invalid_and_negative_amounts(tmp_path: Path) -> None:
    assert write_batches(tmp_path, [], 2) == ()
    assert scan_batches((), None, 0, 100) == (0, 0, 0)
    with pytest.raises(ValueError):
        write_batches(tmp_path, [], 0)
    with pytest.raises(ValueError):
        write_batches(tmp_path, [Order(0, "east", -1, "n")], 2)
