from pathlib import Path

import pytest

from labs.storage.pages.paged import PageReader
from labs.storage.pages.records import write_records
from labs.storage.pages.workload import measure, workloads


def test_workloads_same_records_and_reproducible() -> None:
    sequential, shuffled = workloads(100, 17)
    assert sequential == list(range(100))
    assert sorted(shuffled) == sequential
    assert shuffled != sequential
    assert workloads(100, 17)[1] == shuffled
    with pytest.raises(ValueError):
        workloads(-1, 17)


def test_measure_counts_and_latency_contract(tmp_path: Path) -> None:
    path = tmp_path / "orders.bin"
    write_records(path, 32)
    for keys in workloads(32, 17):
        result = measure(PageReader(path, 64), keys)
        assert result["checksum"] == 4960
        assert result["requests"] == 32
        assert result["page_requests"] == result["file_reads"] == 32
        assert result["unique_pages"] == 4
        assert result["bytes_read"] == 2048
        assert 0 <= result["p50_ns"] <= result["p95_ns"] <= result["max_ns"]
    with pytest.raises(ValueError, match="empty"):
        measure(PageReader(path), [])
    with pytest.raises(ValueError, match="missing"):
        measure(PageReader(path), [32])
