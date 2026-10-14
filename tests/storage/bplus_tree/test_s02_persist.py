import random
from pathlib import Path

import pytest

from labs.storage.bplus_tree.page_file import PAGE_SIZE, load, save
from labs.storage.bplus_tree.tree import BPlusTree, Internal, Leaf


def shape(node: Leaf | Internal) -> object:
    if isinstance(node, Leaf):
        return tuple(node.items)
    return (tuple(node.keys), tuple(shape(child) for child in node.children))


def test_page_topology_survives_reopen_without_reinsert(tmp_path: Path) -> None:
    tree = BPlusTree[int](3, 3)
    keys = list(range(100))
    random.Random(21).shuffle(keys)
    for key in keys:
        tree.insert(key, key * 10)
    path = tmp_path / "tree.pages"
    save(tree, path)
    reopened = load(path)
    assert path.stat().st_size % PAGE_SIZE == 0
    assert shape(reopened.root) == shape(tree.root)
    assert reopened.height == tree.height
    assert reopened.scan(0, 99) == [(key, key * 10) for key in range(100)]
    assert reopened.validate()
    reopened.insert(100, 1000)
    assert reopened.get(100) == 1000 and reopened.validate()


def test_empty_and_signed_values(tmp_path: Path) -> None:
    path = tmp_path / "tree.pages"
    tree = BPlusTree[int](3, 3)
    save(tree, path)
    assert load(path).scan(-10, 10) == []
    tree.insert(-10, -(2**63))
    save(tree, path)
    assert load(path).get(-10) == -(2**63)


def test_corruption_and_truncation_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tree.pages"
    tree = BPlusTree[int](3, 3)
    tree.insert(1, 10)
    save(tree, path)
    original = path.read_bytes()
    for damaged in (original[:-1], original[:PAGE_SIZE], original + b"x"):
        path.write_bytes(damaged)
        with pytest.raises(ValueError):
            load(path)
    damaged = bytearray(original)
    damaged[PAGE_SIZE + 12] ^= 1
    path.write_bytes(damaged)
    with pytest.raises(ValueError, match="checksum"):
        load(path)


def test_unencodable_value_does_not_truncate_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "tree.pages"
    tree = BPlusTree[int](3, 3)
    tree.insert(1, 10)
    save(tree, path)
    before = path.read_bytes()
    tree.insert(2, 2**63)
    with pytest.raises(ValueError, match="64"):
        save(tree, path)
    assert path.read_bytes() == before
