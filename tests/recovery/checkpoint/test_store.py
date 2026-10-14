from __future__ import annotations

import subprocess
import sys

import pytest

from labs.recovery.checkpoint.experiments import generations, publication, snapshot_tail
from labs.recovery.checkpoint.store import Store


def fill(store: Store, start: int, end: int) -> None:
    for position in range(start, end + 1):
        amount = position % 101
        store.commit(position, {"alice": 100 - amount, "bob": 100 + amount})


def test_snapshot_replays_only_tail_and_keeps_nonnegative_balances(tmp_path):
    store = Store(tmp_path)
    fill(store, 1, 100)
    store.snapshot(100)
    fill(store, 101, 105)

    state, position, bytes_read = store.recover()
    expected = sum((tmp_path / f"{n:020d}.wal").stat().st_size for n in range(101, 106))
    assert (state, position, bytes_read) == ({"alice": 96, "bob": 104}, 105, expected)
    assert bytes_read < sum(path.stat().st_size for path in tmp_path.glob("[0-9]*.wal"))


def test_zero_position_snapshot_and_end_position(tmp_path):
    store = Store(tmp_path)
    store.snapshot(0)
    assert store.recover()[:2] == ({"alice": 100, "bob": 100}, 0)
    fill(store, 1, 2)
    assert store.recover()[:2] == ({"alice": 98, "bob": 102}, 2)


def test_negative_balance_is_rejected(tmp_path):
    store = Store(tmp_path)
    with pytest.raises(ValueError, match="invalid committed state"):
        store.commit(1, {"alice": -1, "bob": 201})


@pytest.mark.parametrize("fault,code", [
    ("before_replace", 71),
    ("after_replace", 72),
    ("after_directory_sync", 73),
])
def test_snapshot_crash_boundaries_preserve_recovery(tmp_path, fault, code):
    store = Store(tmp_path)
    fill(store, 1, 5)
    worker = (
        "from pathlib import Path\n"
        "from labs.recovery.checkpoint.store import Store\n"
        "import sys\n"
        "Store(Path(sys.argv[1])).snapshot(5, fault=sys.argv[2])\n"
    )
    result = subprocess.run([sys.executable, "-c", worker, str(tmp_path), fault], timeout=10)
    assert result.returncode == code
    assert Store(tmp_path).recover()[:2] == ({"alice": 95, "bob": 105}, 5)


def test_publication_rejects_unusable_snapshot_without_reclaiming(tmp_path):
    store = Store(tmp_path)
    fill(store, 1, 5)
    store.snapshot(5)
    store.snapshot_path(5).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="no usable recovery base"):
        store.publish([5])
    assert (tmp_path / "00000000000000000001.wal").exists()


def test_corrupt_tail_and_gap_fail_recovery(tmp_path):
    store = Store(tmp_path)
    fill(store, 1, 3)
    store.snapshot(3)
    fill(store, 4, 5)
    (tmp_path / "00000000000000000004.wal").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="no usable recovery base"):
        store.recover()


def test_executable_snapshot_tail_experiment():
    result = snapshot_tail()
    assert result["position"] == 105
    assert result["tail_transactions"] == 5
    assert result["bytes_read"] == result["expected_bytes"]


def test_executable_publication_crash_experiment():
    observed = publication()
    assert len(observed) == 7
    assert observed["publish:after_first_log_delete"] == 74


def test_executable_generation_rotation_experiment():
    result = generations()
    assert result == {
        "fallback_transactions": 15,
        "rotation_exits": [71, 72, 73, 74, 75],
        "continued_position": 31,
    }
