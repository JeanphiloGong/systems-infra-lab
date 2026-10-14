import pytest
from labs.partitioning.skew.skew import aggregate, distribution, route, salted_counts


def test_uniform_and_skew_counts_account_for_every_request() -> None:
    assert sum(distribution([f"k{i}" for i in range(1000)], 4)) == 1000
    counts = distribution(["hot"] * 900 + [f"k{i}" for i in range(100)], 4)
    assert sum(counts) == 1000 and max(counts) >= 900


def test_single_hot_key_cannot_be_split_by_more_nodes() -> None:
    assert max(distribution(["hot"] * 100, 8)) == 100


def test_salt_preserves_total_and_spreads_writes() -> None:
    counts = salted_counts("hot", 100, 4, 4)
    assert counts == [25, 25, 25, 25]
    assert aggregate(["hot"] * 100, 4)[1] == 100


@pytest.mark.parametrize("partitions", [0, -1])
def test_invalid_partition_count(partitions: int) -> None:
    with pytest.raises(ValueError):
        route("key", partitions)
