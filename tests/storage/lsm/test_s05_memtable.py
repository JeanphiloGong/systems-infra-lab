from labs.storage.lsm.memtable import MemTable


def test_sorted_snapshot_and_last_put_wins() -> None:
    table = MemTable()
    assert table.get("absent") is None
    table.put("z", "old")
    table.put("a", "")
    table.put("z", "new")
    snapshot = table.items()
    table.put("b", "later")
    assert snapshot == [("a", ""), ("z", "new")]
    assert table.get("z") == "new"
