import json
import os
from collections.abc import Callable
from pathlib import Path

from labs.storage.wal.framing import decode, encode

INITIAL = {"alice": 100, "bob": 100}


def replay(records: list[dict[str, object]]) -> tuple[dict[str, int], set[str]]:
    state = INITIAL.copy()
    pending: dict[str, dict[str, int]] = {}
    used: set[str] = set()
    committed: set[str] = set()
    for record in records:
        tx = record.get("tx")
        if not isinstance(tx, str) or not tx or tx in committed:
            raise ValueError("invalid transaction sequence")
        if record.get("kind") == "set":
            if set(record) != {"kind", "tx", "key", "value"}:
                raise ValueError("invalid set fields")
            key, value = record["key"], record["value"]
            if not isinstance(key, str) or key not in INITIAL:
                raise ValueError("unknown account")
            if type(value) is not int or value < 0:
                raise ValueError("invalid balance")
            pending.setdefault(tx, {})[key] = value
            used.add(tx)
        elif record.get("kind") == "commit":
            if set(record) != {"kind", "tx"} or tx not in pending:
                raise ValueError("commit without operations")
            state.update(pending.pop(tx))
            committed.add(tx)
        else:
            raise ValueError("unknown record kind")
    return state, used


class Store:
    def __init__(self, directory: Path, event: Callable[[str], None] | None = None) -> None:
        self.event = event
        self.log_path = directory / "wal.bin"
        self.data_path = directory / "data.json"
        if not self.log_path.exists():
            with self.log_path.open("xb") as log:
                log.flush()
                os.fsync(log.fileno())
            self.emit("wal_created")
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        self.emit("directory_synced")

    def emit(self, name: str) -> None:
        if self.event is not None:
            self.event(name)

    def recover(self) -> dict[str, int]:
        records, _, _ = decode(self.log_path.read_bytes())
        state, _ = replay(records)
        return state

    def commit(self, tx: str, changes: dict[str, int]) -> dict[str, int]:
        records, valid_end, incomplete = decode(self.log_path.read_bytes())
        _, used = replay(records)
        if not isinstance(tx, str) or not tx or tx in used:
            raise ValueError("transaction id empty or already used")
        if not changes:
            raise ValueError("empty transaction")
        operations = [
            {"kind": "set", "tx": tx, "key": key, "value": value}
            for key, value in changes.items()
        ]
        marker = {"kind": "commit", "tx": tx}
        state, _ = replay(records + operations + [marker])
        frames = [encode(record) for record in operations + [marker]]
        if incomplete:
            with self.log_path.open("r+b") as log:
                log.truncate(valid_end)
                log.flush()
                os.fsync(log.fileno())
            self.emit("tail_repaired")
        with self.log_path.open("ab") as log:
            for index, frame in enumerate(frames):
                log.write(frame)
                name = f"operation_{index + 1}_written" if index < len(operations) else "commit_written"
                self.emit(name)
            log.flush()
            self.emit("wal_flushed")
            os.fsync(log.fileno())
            self.emit("wal_synced")
        self.data_path.write_text(json.dumps(state))
        self.emit("data_written")
        self.emit("before_ack")
        return state
