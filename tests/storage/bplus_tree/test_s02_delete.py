from labs.storage.bplus_tree.tree import BPlusTree
import random


def test_delete_and_root_shrink() -> None:
    tree = BPlusTree[int](3, 3)
    for key in range(12):
        tree.insert(key, key)
    for key in range(12):
        assert tree.delete(key) is True
        assert tree.get(key) is None
        assert tree.validate()
    assert tree.height == 1
    assert tree.scan(-1, 20) == []


def test_missing_delete_is_noop() -> None:
    tree = BPlusTree[int](3, 3)
    tree.insert(1, 10)
    assert tree.delete(2) is False
    assert tree.get(1) == 10


def test_delete_rebalances_multiple_internal_levels() -> None:
    for leaf_capacity, internal_capacity in ((2, 3), (3, 4), (4, 5), (7, 8)):
        tree = BPlusTree[int](leaf_capacity, internal_capacity)
        expected = {key: key * 10 for key in range(240)}
        for key, value in expected.items():
            tree.insert(key, value)
        order = list(expected)
        random.Random(20261013 + leaf_capacity).shuffle(order)
        for key in order:
            assert tree.delete(key)
            del expected[key]
            assert tree.validate()
            assert tree.scan(-1, 1000) == sorted(expected.items())
        assert tree.height == 1


def test_delete_missing_key_preserves_deep_tree() -> None:
    tree = BPlusTree[int](3, 4)
    for key in range(100):
        tree.insert(key, key)
    before = tree.scan(-1, 200)
    assert tree.delete(1000) is False
    assert tree.validate()
    assert tree.scan(-1, 200) == before
