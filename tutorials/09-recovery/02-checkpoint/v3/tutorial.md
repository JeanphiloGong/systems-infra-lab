# A02 v3: retained generations and fallback

The v3 checkpoint retains two independently validated snapshot generations. Recovery tries the newest generation first, then an older generation with its required WAL tail. Corrupt bases and missing required logs produce explicit recovery errors.

将下面的完整代码保存为 `labs/storage/wal/framing.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/wal/framing.py -->

```python
import json
from struct import Struct
import zlib

HEADER = Struct("<II")
CRC = Struct("<I")
MAX_PAYLOAD = 1024 * 1024


def encode(record: dict[str, object]) -> bytes:
    payload = json.dumps(record, separators=(",", ":"), sort_keys=True).encode("utf-8")
    size = len(payload)
    if size > MAX_PAYLOAD:
        raise ValueError("payload too large")
    return HEADER.pack(size, size ^ 0xFFFFFFFF) + payload + CRC.pack(zlib.crc32(payload))


def decode(data: bytes) -> tuple[list[dict[str, object]], int, bool]:
    records: list[dict[str, object]] = []
    position = 0
    while position < len(data):
        if len(data) - position < HEADER.size:
            return records, position, True
        size, complement = HEADER.unpack_from(data, position)
        if complement != size ^ 0xFFFFFFFF or not 0 < size <= MAX_PAYLOAD:
            raise ValueError("invalid frame header")
        end = position + HEADER.size + size + CRC.size
        if end > len(data):
            return records, position, True
        payload = data[position + HEADER.size:end - CRC.size]
        checksum = CRC.unpack_from(data, end - CRC.size)[0]
        if checksum != zlib.crc32(payload):
            raise ValueError("payload checksum mismatch")
        record = json.loads(payload)
        if not isinstance(record, dict):
            raise ValueError("frame payload must be an object")
        records.append(record)
        position = end
    return records, position, False
```

将下面的完整代码保存为 `labs/recovery/checkpoint/baseline.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/recovery/checkpoint/baseline.py -->

```python
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
```

将下面的完整代码保存为 `labs/recovery/checkpoint/store.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/recovery/checkpoint/store.py -->

```python
"""Paused single writer: CRC snapshots, retained generations and immutable WAL."""
from __future__ import annotations

import os
from pathlib import Path

from labs.recovery.checkpoint.baseline import commit as commit_segment
from labs.recovery.checkpoint.baseline import replay
from labs.storage.wal.framing import decode, encode


INITIAL = {"alice": 100, "bob": 100}


def valid_state(state):
    return (isinstance(state, dict) and set(state) == set(INITIAL)
            and all(type(value) is int and value >= 0 for value in state.values())
            and sum(state.values()) == 200)


class Store:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def sync_directory(self):
        descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def atomic(self, path, record, fault=None):
        temporary = path.with_suffix('.tmp')
        with temporary.open('wb') as stream:
            stream.write(encode(record))
            stream.flush()
            os.fsync(stream.fileno())
        if fault == 'before_replace':
            os._exit(71)
        os.replace(temporary, path)
        if fault == 'after_replace':
            os._exit(72)
        self.sync_directory()
        if fault == 'after_directory_sync':
            os._exit(73)

    def record(self, path):
        rows, _, incomplete = decode(path.read_bytes())
        if incomplete or len(rows) != 1:
            raise ValueError('invalid metadata frame')
        return rows[0]

    def manifest(self):
        path = self.directory / 'manifest.wal'
        if not path.exists():
            return None
        record = self.record(path)
        positions = record.get('snapshots')
        required = record.get('required_through')
        if (record.get('format') != 1 or not isinstance(positions, list) or not positions
                or any(type(n) is not int or n < 0 for n in positions)
                or positions != sorted(set(positions)) or type(required) is not int
                or required < positions[-1]):
            raise ValueError('invalid manifest')
        return record

    def snapshot_path(self, position):
        return self.directory / f'snapshot-{position:020d}.wal'

    def read_snapshot(self, position):
        record = self.record(self.snapshot_path(position))
        if record.get('format') != 1 or record.get('position') != position or not valid_state(record.get('state')):
            raise ValueError('invalid snapshot')
        return record['state']

    def tail(self, state, position, required):
        byte_count = 0
        for path in sorted(self.directory.glob('[0-9]*.wal')):
            try:
                number = int(path.stem)
            except ValueError:
                raise ValueError('invalid segment name') from None
            if number <= position:
                continue
            if path.name != f'{position + 1:020d}.wal':
                raise ValueError('required log segment is missing')
            data = path.read_bytes()
            rows, _, incomplete = decode(data)
            if (incomplete or len(rows) != 3
                    or any(row.get('tx') != str(number) for row in rows)
                    or [row.get('kind') for row in rows] != ['set', 'set', 'commit']
                    or {row.get('key') for row in rows[:2]} != set(INITIAL)):
                raise ValueError('invalid published transaction')
            state, _ = replay(rows)
            if not valid_state(state):
                raise ValueError('invalid balance')
            position = number
            byte_count += len(data)
        if position < required:
            raise ValueError('required log segment is missing')
        return dict(state), position, byte_count

    def recover(self):
        manifest = self.manifest()
        if manifest is None:
            return self.tail(dict(INITIAL), 0, 0)
        failures = []
        for position in reversed(manifest['snapshots']):
            try:
                state = self.read_snapshot(position)
                return self.tail(state, position, manifest['required_through'])
            except (ValueError, OSError) as error:
                failures.append(str(error))
        raise ValueError('no usable recovery base: ' + '; '.join(failures))

    def commit(self, position, state):
        if type(position) is not int or not valid_state(state):
            raise ValueError('invalid committed state')
        _, last, _ = self.recover()
        if position != last + 1:
            raise ValueError('commit position must be next')
        commit_segment(self.directory, position, state)

    def snapshot(self, position, *, fault=None):
        state, recovered, _ = self.recover()
        if type(position) is not int or position != recovered:
            raise ValueError('snapshot position must equal recovered prefix')
        self.atomic(self.snapshot_path(position), dict(format=1, position=position, state=state), fault)
        previous = self.manifest()
        positions = sorted(set((previous['snapshots'] if previous else []) + [position]))
        # Publishing this pointer makes v1 recovery use the snapshot; logs stay intact.
        self.atomic(self.directory / 'manifest.wal', dict(format=1, snapshots=positions, required_through=position))

    def publish(self, positions, *, fault=None, keep=2):
        if (type(keep) is not int or keep < 1 or not positions
                or any(type(n) is not int or n < 0 for n in positions)
                or positions != sorted(set(positions))):
            raise ValueError('invalid retained generations')
        selected = positions[-keep:]
        current, tip, _ = self.recover()
        # Every retained base must independently recover the SAME full prefix.
        for position in selected:
            state = self.read_snapshot(position)
            result, end, _ = self.tail(state, position, tip)
            if end != tip or result != current:
                raise ValueError('snapshot does not match durable history')
        self.atomic(self.directory / 'manifest.wal', dict(format=1, snapshots=selected, required_through=tip), fault)
        for path in sorted(self.directory.glob('[0-9]*.wal')):
            if int(path.stem) <= selected[0]:
                path.unlink()
                if fault == 'after_first_log_delete':
                    os._exit(74)
        self.sync_directory()
        for path in sorted(self.directory.glob('snapshot-*.wal')):
            if path not in [self.snapshot_path(n) for n in selected]:
                path.unlink()
                if fault == 'after_first_snapshot_delete':
                    os._exit(75)
        self.sync_directory()
```

Optional: use [参考分支检查](../../../../docs/reference-checks.md). The v3 checks corrupt the latest snapshot, verify fallback through 15 WAL transactions, reject a missing required segment, and cover generation rotation crash exits 71 through 75.

## 直接验证本版

先按上面的完整路径保存依赖文件，再从仓库根目录运行下面的完整检查。它只使用临时目录，不依赖 reference 的测试文件。

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.recovery.checkpoint.store import Store

with TemporaryDirectory() as folder:
    directory = Path(folder)
    store = Store(directory)
    store.commit(1, {"alice": 90, "bob": 110})
    store.snapshot(1)
    store.commit(2, {"alice": 80, "bob": 120})
    store.snapshot(2)
    store.publish([1, 2])
    store.snapshot_path(2).write_bytes(b"broken snapshot")
    state, position, byte_count = Store(directory).recover()
    assert state == {"alice": 80, "bob": 120} and position == 2 and byte_count > 0
    (directory / f"{2:020d}.wal").unlink()
    try:
        Store(directory).recover()
    except ValueError:
        pass
    else:
        raise AssertionError("fallback without required WAL was accepted")
print("v3 fallback and missing-tail rejection ok")
PY
```

应输出代码末尾的 `ok` 信息且没有断言失败。这个小检查验证本版所示的恢复行为；它没有覆盖全部崩溃注入点或断电恢复。

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/recovery/checkpoint/test_store.py -q
```

</details>
