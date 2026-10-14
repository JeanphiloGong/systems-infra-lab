import pytest

from labs.transactions.mvcc.model import visible


def test_v1_old_and_new_snapshot_match_database_trace() -> None:
    versions = [(1, True), (2, False)]
    assert visible(versions, 1) is True
    assert visible(versions, 2) is False
    assert visible(versions, 9) is False


def test_v1_before_creation_has_no_visible_value() -> None:
    with pytest.raises(LookupError):
        visible([(2, True)], 1)
    with pytest.raises(LookupError):
        visible([], 1)
