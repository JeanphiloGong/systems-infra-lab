import json
from pathlib import Path

from labs.storage.wal.framing import decode, encode

INITIAL = {"alice": 100, "bob": 100}


def prepare(data_path: Path, log_path: Path, apply: bool) -> None:
    operations = [
        {"kind": "set", "tx": "t1", "key": "alice", "value": 90},
        {"kind": "set", "tx": "t1", "key": "bob", "value": 110},
    ]
    with log_path.open("xb") as log:
        for operation in operations:
            log.write(encode(operation))
    if apply:
        data_path.write_text(json.dumps({"alice": 90, "bob": 110}))


def inspect_pending(log_path: Path) -> tuple[dict[str, int], set[str]]:
    records, _, _ = decode(log_path.read_bytes())
    candidate = INITIAL.copy()
    pending: set[str] = set()
    for record in records:
        if set(record) != {"kind", "tx", "key", "value"} or record["kind"] != "set":
            raise ValueError("expected set operation")
        tx, key, value = record["tx"], record["key"], record["value"]
        if not isinstance(tx, str) or not tx or not isinstance(key, str):
            raise ValueError("invalid operation")
        if key not in INITIAL or type(value) is not int or value < 0:
            raise ValueError("invalid operation")
        candidate[key] = value
        pending.add(tx)
    return candidate, pending
