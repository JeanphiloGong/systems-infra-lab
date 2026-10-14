import json
from pathlib import Path
import subprocess
import sys

import pytest

from labs.storage.wal.store import Store


POINTS = [
    "wal_created", "directory_synced", "operation_1_written", "operation_2_written",
    "commit_written", "wal_flushed", "wal_synced", "data_written", "before_ack", "after_ack",
]


@pytest.mark.parametrize("point", POINTS)
def test_real_process_crash_and_fresh_recovery(tmp_path: Path, point: str) -> None:
    result = subprocess.run([
        sys.executable, "-m", "labs.storage.wal.crash_worker", str(tmp_path), "write", "--crash-at", point,
    ], text=True, capture_output=True, check=False)
    assert result.returncode == 73
    if point == "after_ack":
        assert "ACK" in result.stdout
    else:
        assert "ACK" not in result.stdout
    recovered = []
    for _ in range(2):
        read = subprocess.run([
            sys.executable, "-m", "labs.storage.wal.crash_worker", str(tmp_path), "recover",
        ], text=True, capture_output=True, check=True)
        recovered.append(json.loads(read.stdout))
    initial = {"alice": 100, "bob": 100}
    committed = {"alice": 90, "bob": 110}
    assert recovered[0] in (initial, committed)
    assert recovered[0] == recovered[1]
    if point in ("wal_flushed", "wal_synced", "data_written", "before_ack", "after_ack"):
        assert recovered[0] == committed


@pytest.mark.parametrize("point", POINTS[1:])
def test_previous_commit_survives_next_transaction_crash(tmp_path: Path, point: str) -> None:
    store = Store(tmp_path)
    store.commit("t0", {"alice": 95, "bob": 105})
    result = subprocess.run([
        sys.executable, "-m", "labs.storage.wal.crash_worker", str(tmp_path), "write", "--crash-at", point,
    ], text=True, capture_output=True, check=False)
    assert result.returncode == 73
    read = subprocess.run([
        sys.executable, "-m", "labs.storage.wal.crash_worker", str(tmp_path), "recover",
    ], text=True, capture_output=True, check=True)
    assert json.loads(read.stdout) in (
        {"alice": 95, "bob": 105}, {"alice": 90, "bob": 110},
    )


def test_crash_after_tail_repair_preserves_old_commit_and_allows_append(tmp_path: Path) -> None:
    store = Store(tmp_path)
    previous = {"alice": 95, "bob": 105}
    store.commit("t0", previous)
    with store.log_path.open("ab") as log:
        log.write(b"abc")
    command = [sys.executable, "-m", "labs.storage.wal.crash_worker", str(tmp_path)]
    result = subprocess.run(command + ["write", "--crash-at", "tail_repaired"],
                            text=True, capture_output=True, check=False)
    assert result.returncode == 73
    assert "ACK" not in result.stdout
    for _ in range(2):
        read = subprocess.run(command + ["recover"], text=True, capture_output=True, check=True)
        assert json.loads(read.stdout) == previous
    next_write = subprocess.run(command + ["write"], text=True, capture_output=True, check=True)
    assert "ACK" in next_write.stdout
    read = subprocess.run(command + ["recover"], text=True, capture_output=True, check=True)
    assert json.loads(read.stdout) == {"alice": 90, "bob": 110}
