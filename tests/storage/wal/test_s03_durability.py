import os
from pathlib import Path

import pytest

from labs.storage.wal.store import Store


def test_flush_sync_and_confirmation_order(tmp_path: Path) -> None:
    events: list[str] = []
    store = Store(tmp_path, event=events.append)
    assert events == ["wal_created", "directory_synced"]
    store.commit("t1", {"alice": 90, "bob": 110})
    assert events[2:] == [
        "operation_1_written", "operation_2_written", "commit_written",
        "wal_flushed", "wal_synced", "data_written", "before_ack",
    ]


def test_fsync_failure_never_reaches_ack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    store = Store(tmp_path, event=events.append)
    def fail_sync(fd: int) -> None:
        raise OSError("injected fsync failure")
    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(OSError, match="injected"):
        store.commit("t1", {"alice": 90, "bob": 110})
    assert "wal_flushed" in events
    assert "wal_synced" not in events
    assert "before_ack" not in events
    assert store.recover() == {"alice": 90, "bob": 110}


def test_tail_repair_is_synced_before_append(tmp_path: Path) -> None:
    events: list[str] = []
    store = Store(tmp_path, event=events.append)
    store.log_path.write_bytes(b"abc")
    events.clear()
    store.commit("t1", {"alice": 90, "bob": 110})
    assert events[:2] == ["tail_repaired", "operation_1_written"]
