import pytest

from labs.storage.bplus_tree.leaf import LeafPage


def test_capacity_and_overwrite_policy() -> None:
    leaf = LeafPage(capacity=3)
    assert leaf.insert(20, "a") == 0
    assert leaf.insert(10, "b") == 1
    assert leaf.insert(30, "c") == 0
    assert leaf.items == [(10, "b"), (20, "a"), (30, "c")]
    assert leaf.insert(20, "updated") == 0
    assert leaf.items == [(10, "b"), (20, "updated"), (30, "c")]
    with pytest.raises(OverflowError):
        leaf.insert(40, "d")


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError):
        LeafPage(0)
