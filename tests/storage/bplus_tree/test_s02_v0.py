from labs.storage.bplus_tree.array_index import OrderedIndex


def test_insert_keeps_keys_sorted_and_counts_shifts() -> None:
    index = OrderedIndex()
    assert index.get(7) is None
    assert index.insert(20, "twenty") == 0
    assert index.insert(40, "forty") == 0
    assert index.insert(30, "thirty") == 1
    assert index.keys == [20, 30, 40]
    assert index.get(30) == "thirty"
    assert index.get(99) is None


def test_duplicate_overwrites_without_extra_entry() -> None:
    index = OrderedIndex()
    index.insert(1, "old")
    assert index.insert(1, "new") == 0
    assert index.keys == [1]
    assert index.get(1) == "new"
