from pathlib import Path

from labs.storage.bloom.table import ImmutableTable
from labs.storage.lsm.sstable import SSTable


def test_filter_skips_negative_file_read_but_preserves_results(tmp_path: Path) -> None:
    path = tmp_path / "table.jsonl"
    SSTable.create(path, {"a": "1", "b": "2"})
    table = ImmutableTable(path)
    assert table.query("missing") == (None, 0)
    assert table.query("a") == ("1", 1)
    assert table.build_reads == 1
    assert table.query_reads == 1


def test_every_key_in_file_enters_filter(tmp_path: Path) -> None:
    path = tmp_path / "table.jsonl"
    SSTable.create(path, {"a": "1", "b": "2"})
    table = ImmutableTable(path)
    assert table.query("b") == ("2", 1)


def test_false_positive_requires_real_lookup_and_returns_missing(tmp_path: Path) -> None:
    path = tmp_path / "table.jsonl"
    SSTable.create(path, {"a": "", "订单": "value"})
    table = ImmutableTable(path, bits=1, hashes=1)
    assert table.query("missing") == (None, 1)
    assert table.query("a") == ("", 1)
    assert table.query("订单") == ("value", 1)
    assert table.query_reads == 3
    reopened = ImmutableTable(path)
    assert reopened.query("订单")[0] == "value"
    assert reopened.build_reads == 1


def test_results_match_real_sstable_and_actual_open_counts(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "table.jsonl"
    records = {f"key-{index:03}": str(index) for index in range(100)}
    SSTable.create(path, records)
    calls = []
    original = Path.open
    def count_open(self, *args, **kwargs):
        if self == path:
            calls.append(self)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", count_open)
    table = ImmutableTable(path, bits=8192, hashes=4)
    assert len(calls) == table.build_reads == 1
    for key in records:
        assert table.query(key)[0] == records[key]
    for index in range(200):
        assert table.query(f"absent-{index}")[0] is None
    assert table.query_reads < 300
    assert len(calls) == table.build_reads + table.query_reads
