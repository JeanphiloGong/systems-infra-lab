import random

from labs.storage.bplus_tree.tree import BPlusTree


def test_split_new_root_and_lookup() -> None:
    tree = BPlusTree(leaf_capacity=3, internal_capacity=3)
    for key in (30, 10, 20, 40, 50, 60):
        tree.insert(key, str(key))
    assert [tree.get(key) for key in range(10, 61, 10)] == [str(key) for key in range(10, 61, 10)]
    assert tree.height >= 2
    assert tree.validate()


def test_random_insert_reference_and_range() -> None:
    keys = list(range(100))
    random.Random(7).shuffle(keys)
    tree = BPlusTree(leaf_capacity=4, internal_capacity=4)
    expected: dict[int, int] = {}
    for key in keys:
        tree.insert(key, key * 10)
        expected[key] = key * 10
        assert tree.validate()
    assert all(tree.get(key) == value for key, value in expected.items())
    assert tree.scan(17, 24) == [(key, key * 10) for key in range(17, 25)]
    assert tree.scan(100, 200) == []
