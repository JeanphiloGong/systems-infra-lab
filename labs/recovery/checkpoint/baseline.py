"""A02 v0: replay immutable, contiguous transaction segments in full."""

import os
from pathlib import Path

from labs.storage.wal.framing import decode, encode


def replay(records: list[dict[str, object]]) -> tuple[dict[str, int], set[str]]:
    state = {"alice": 100, "bob": 100}
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
            if not isinstance(key, str) or key not in state or type(value) is not int or value < 0:
                raise ValueError("invalid balance")
            pending.setdefault(tx, {})[key] = value
        elif record.get("kind") == "commit":
            if set(record) != {"kind", "tx"} or tx not in pending:
                raise ValueError("commit without operations")
            state.update(pending.pop(tx))
            committed.add(tx)
        else:
            raise ValueError("unknown record kind")
    return state, used


def commit(directory: Path, number: int, balances: dict[str, int]) -> None:
    if type(number) is not int or number < 1:
        raise ValueError("positive transaction number required")
    if set(balances) != {"alice", "bob"} or sum(balances.values()) != 200:
        raise ValueError("transfer must preserve both accounts and total")
    records = [
        {"kind": "set", "tx": str(number), "key": key, "value": value}
        for key, value in balances.items()
    ] + [{"kind": "commit", "tx": str(number)}]
    replay(records)
    target = directory / f"{number:020d}.wal"
    if target.exists():
        raise FileExistsError(target)
    temporary = target.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        stream.write(b"".join(encode(record) for record in records))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def recover(directory: Path) -> tuple[dict[str, int], int, int]:
    records = []
    transactions = byte_count = 0
    for expected, path in enumerate(sorted(directory.glob("*.wal")), start=1):
        if path.name != f"{expected:020d}.wal":
            raise ValueError("gap in committed segments")
        data = path.read_bytes()
        decoded, _, incomplete = decode(data)
        if incomplete or len(decoded) != 3:
            raise ValueError("incomplete published transaction")
        if any(record.get("tx") != str(expected) for record in decoded):
            raise ValueError("transaction position mismatch")
        state, _ = replay(decoded)
        if (
            decoded[-1].get("kind") != "commit"
            or {record.get("key") for record in decoded[:-1]} != {"alice", "bob"}
            or sum(state.values()) != 200
        ):
            raise ValueError("invalid transfer")
        records.extend(decoded)
        transactions += 1
        byte_count += len(data)
    state, _ = replay(records)
    return state, transactions, byte_count
