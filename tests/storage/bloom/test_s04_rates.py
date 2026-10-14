import pytest

from labs.storage.bloom.filter import theoretical_false_positive_rate
from labs.storage.bloom.measure import sweep


def test_sweep_varies_all_three_parameters_and_reports_counts() -> None:
    rows = sweep([512, 2048], [1, 4], [40, 160], probes=2000)
    assert len(rows) == 8
    assert len({row["bits"] for row in rows}) == 2
    assert len({row["hashes"] for row in rows}) == 2
    assert len({row["inserted"] for row in rows}) == 2
    for row in rows:
        assert row["bytes"] == (row["bits"] + 7) // 8
        assert row["measured"] == row["false_positives"] / 2000
        assert 0 <= row["measured"] <= 1
        assert 0 <= row["theory"] <= 1
        assert row["false_negatives"] == 0
    assert rows == sweep([512, 2048], [1, 4], [40, 160], probes=2000)


def test_formula_empty_and_invalid_arguments() -> None:
    assert theoretical_false_positive_rate(512, 4, 0) == 0
    for values in ((0, 4, 10), (512, 0, 10), (512, 4, -1)):
        with pytest.raises(ValueError):
            theoretical_false_positive_rate(*values)
    with pytest.raises(ValueError):
        sweep([512], [4], [10], probes=0)
