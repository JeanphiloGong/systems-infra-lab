from labs.query.planner.model import Stats, choose, estimate_join


def test_selectivity_changes_plan() -> None:
    assert choose(Stats(1000, 100), 1)[0] == "index"
    assert choose(Stats(1000, 1), 1)[0] == "seq"


def test_stale_stats_change_estimate() -> None:
    stale = choose(Stats(1000, 100), 1); fresh = choose(Stats(1000, 2), 1)
    assert stale != fresh


def test_correlation_breaks_independence_assumption() -> None:
    assert estimate_join(Stats(100, 10), Stats(100, 10), True) > estimate_join(Stats(100, 10), Stats(100, 10), False)
