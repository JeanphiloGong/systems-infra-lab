import pytest

from labs.partitioning.routing.ring import HashRing


def test_membership_order_does_not_change_ring() -> None:
    first = HashRing(("a", "b", "c"), 16)
    reordered = HashRing(("c", "a", "b"), 16)
    assert first.points == reordered.points
    assert all(first.node(key) == reordered.node(key) for key in range(1000))


def test_addition_only_moves_keys_to_added_node() -> None:
    old = HashRing(("a", "b", "c"), 64)
    new = HashRing(("a", "b", "c", "d"), 64)
    moved = [(old.node(key), new.node(key)) for key in range(10000) if old.node(key) != new.node(key)]
    assert moved
    assert all(target == "d" for _, target in moved)


def test_removal_only_moves_keys_from_removed_node() -> None:
    old = HashRing(("a", "b", "c"), 64)
    new = HashRing(("a", "c"), 64)
    moved = [(old.node(key), new.node(key)) for key in range(10000) if old.node(key) != new.node(key)]
    assert moved
    assert all(source == "b" for source, _ in moved)


def test_wrap_and_exact_position() -> None:
    ring = HashRing(("a", "b"), 2)
    assert ring.owner_at(ring.points[0]) == ring.owners[0]
    assert ring.owner_at(ring.points[-1] + 1) == ring.owners[0]
    assert ring.owner_at(0) == ring.owners[0]


@pytest.mark.parametrize("nodes,count", [((), 1), (("a", "a"), 1), (("a",), 0), (("a",), -1)])
def test_invalid_ring_configuration(nodes: tuple[str, ...], count: int) -> None:
    with pytest.raises(ValueError):
        HashRing(nodes, count)
