import pytest

from labs.partitioning.routing.ranges import RangeMap


def test_half_open_boundaries() -> None:
    route = RangeMap((100, 200), ("a", "b", "c"))
    assert [route.node(key) for key in (-1, 99, 100, 199, 200, 999)] == ["a", "a", "b", "b", "c", "c"]


def test_query_selects_only_overlapping_shards() -> None:
    route = RangeMap((100, 200), ("a", "b", "c"))
    assert route.covering(99, 100) == ("a",)
    assert route.covering(99, 101) == ("a", "b")
    assert route.covering(100, 200) == ("b",)
    assert route.covering(-100, 999) == ("a", "b", "c")
    assert route.covering(100, 100) == ()
    assert route.covering(200, 100) == ()


@pytest.mark.parametrize("cuts,nodes", [((100, 100), ("a", "b", "c")), ((200, 100), ("a", "b", "c")), ((100,), ("a",)), ((), ()), ((), ("a", "a"))])
def test_rejects_invalid_ranges(cuts: tuple[int, ...], nodes: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        RangeMap(cuts, nodes)


def test_single_range_covers_all_integer_keys() -> None:
    route = RangeMap((), ("only",))
    assert route.node(10**20) == "only"
    assert route.covering(-10**20, 10**20) == ("only",)
