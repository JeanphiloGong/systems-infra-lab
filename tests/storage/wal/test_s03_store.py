import json
from pathlib import Path

import pytest

from labs.storage.wal.framing import encode
from labs.storage.wal.store import Store


def test_committed_group_and_incomplete_group(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.commit("t1", {"alice": 90, "bob": 110})
    with store.log_path.open("ab") as log:
        log.write(encode({"kind": "set", "tx": "t2", "key": "alice", "value": 80}))
    assert store.recover() == {"alice": 90, "bob": 110}
    assert store.recover() == store.recover()
    store.data_path.write_text("broken json")
    assert store.recover() == {"alice": 90, "bob": 110}


def test_abandoned_and_partial_tail_do_not_hide_next_commit(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.log_path.write_bytes(encode({"kind": "set", "tx": "abandoned", "key": "alice", "value": 1}) + b"abc")
    assert store.recover() == {"alice": 100, "bob": 100}
    store.commit("t2", {"alice": 70, "bob": 130})
    assert store.recover() == {"alice": 70, "bob": 130}


def test_duplicate_transaction_and_corrupt_log_rejected(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.commit("t1", {"alice": 90, "bob": 110})
    with pytest.raises(ValueError, match="used"):
        store.commit("t1", {"alice": 80, "bob": 120})
    data = bytearray(store.log_path.read_bytes())
    data[9] ^= 1
    store.log_path.write_bytes(data)
    with pytest.raises(ValueError, match="checksum"):
        store.recover()


def test_invalid_transaction_before_append(tmp_path: Path) -> None:
    store = Store(tmp_path)
    before = store.log_path.read_bytes()
    for changes in ({}, {"eve": 10}, {"alice": -1}, {"alice": True}):
        with pytest.raises(ValueError):
            store.commit("t1", changes)
        assert store.log_path.read_bytes() == before
