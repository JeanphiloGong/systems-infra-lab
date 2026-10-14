from pathlib import Path

import pytest

from labs.storage.pages.paged import PageReader
from labs.storage.pages.records import write_records
from labs.storage.pages.workload import measure, workloads


def test_lru_eviction_reload_and_capacity(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 4)
    reader = PageReader(path, 8, capacity=2)
    for key in (0, 1, 0, 2):
        assert reader.get(key) == key * 10
        assert len(reader.cache) <= 2
    assert list(reader.cache) == [0, 2]
    assert reader.file_reads == 3
    assert reader.get(1) == 10
    assert reader.file_reads == 4
    assert list(reader.cache) == [2, 1]


def test_cross_page_with_one_cache_slot(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 3)
    reader = PageReader(path, 3, capacity=1)
    for _ in range(2):
        assert [reader.get(key) for key in range(3)] == [0, 10, 20]
        assert len(reader.cache) == 1


def test_cold_warm_and_working_set_overflow(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 32)
    seq, shuffled = workloads(32, 17)
    reader = PageReader(path, 64, capacity=4)
    cold = measure(reader, seq)
    warm = measure(reader, shuffled)
    assert cold["file_reads"] == 4
    assert cold["bytes_read"] == 256
    assert warm["file_reads"] == warm["bytes_read"] == 0
    assert warm["page_requests"] == 32
    small = measure(PageReader(path, 64, capacity=1), shuffled)
    assert small["file_reads"] > cold["file_reads"]
    assert small["checksum"] == warm["checksum"] == 4960


def test_negative_capacity_rejected(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 0)
    with pytest.raises(ValueError, match="capacity"):
        PageReader(path, capacity=-1)
