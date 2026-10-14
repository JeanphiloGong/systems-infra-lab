import pytest
from labs.partitioning.skew.skew import profile, split_counter
from labs.partitioning.skew.queues import simulate


def test_requests_and_data_are_different() -> None:
    report = profile(["hot"]*900+[f"cold{i}" for i in range(100)],4)
    assert sum(report["distinct_keys"]) == 101
    assert sum(report["requests"]) == 1000


def test_actual_counter_sum_and_read_amplification() -> None:
    assert split_counter(103,4,4) == ([26,26,26,25],103,4)
    assert split_counter(0,4,4) == ([0,0,0,0],0,4)


def test_single_hot_key_queue_does_not_scale_but_split_does() -> None:
    keys = ["hot"]*1000
    four = simulate(keys,4,2)
    eight = simulate(keys,8,2)
    split = simulate(keys,8,2,salts=8)
    assert four["p99"] == eight["p99"] > 400
    assert split["p99"] == 1
    assert four["capacity_bound"] == 1
    assert split["capacity_bound"] == 8
    bottleneck = simulate(keys,8,2,salts=8,shared_service=1)
    assert bottleneck["capacity_bound"] == 1
    assert bottleneck["p99"] > 400


def test_empty_and_invalid() -> None:
    assert simulate([],4,1)["total"] == 0
    assert simulate([],4,1)["capacity_bound"] is None
    for rate in (0,-1,float("nan"),float("inf")):
        with pytest.raises(ValueError):
            simulate(["x"],4,rate)
