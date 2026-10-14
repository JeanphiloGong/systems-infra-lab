import pytest

from labs.partitioning.routing.hashing import modulo_node, stable_hash


def test_stable_hash_known_value() -> None:
    assert stable_hash("abc") == int.from_bytes(bytes.fromhex("ba7816bf8f01cfea"), "big")


def test_modulo_routes_same_key_to_same_node() -> None:
    nodes = ("a", "b", "c")
    assert modulo_node(123, nodes) == modulo_node(123, nodes)
    assert all(modulo_node(key, nodes) in nodes for key in range(1000))
    assert modulo_node(-1, ("only",)) == "only"


def test_node_count_changes_existing_routes() -> None:
    old, new = ("a", "b", "c"), ("a", "b", "c", "d")
    moved = sum(modulo_node(key, old) != modulo_node(key, new) for key in range(1000))
    assert 650 < moved < 850


@pytest.mark.parametrize("nodes", [(), ("a", "a")])
def test_invalid_node_configuration(nodes: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        modulo_node(0, nodes)
