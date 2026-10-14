from pathlib import Path

import pytest

from labs.storage.pages.paged import PageReader
from labs.storage.pages.records import write_records


def test_cross_page_and_partial_final_page(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 3)
    reader = PageReader(path, page_size=10)
    assert reader.get(1) == 10
    assert reader.bytes_read == 20
    assert reader.page_requests == 2
    assert reader.get(2) == 20
    assert reader.bytes_read == 34
    assert reader.pages_seen == {0, 1, 2}
    assert reader.get(3) is None
    assert reader.get(-1) is None
    assert reader.page_requests == 4


@pytest.mark.parametrize("page_size", [1, 7, 8, 10, 16, 4096])
def test_all_records_for_page_sizes(tmp_path: Path, page_size: int) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 31)
    reader = PageReader(path, page_size)
    assert [reader.get(key) for key in range(31)] == [key * 10 for key in range(31)]


def test_invalid_page_size_and_truncated_file(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 0)
    with pytest.raises(ValueError, match="page_size"):
        PageReader(path, 0)
    assert PageReader(path, 10).get(0) is None
    path.write_bytes(b"bad")
    with pytest.raises(ValueError, match="truncated"):
        PageReader(path, 10)
