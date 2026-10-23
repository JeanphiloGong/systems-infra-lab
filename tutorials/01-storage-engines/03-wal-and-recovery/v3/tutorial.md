# S03 v3：让提交标记决定哪些操作可见

前置 [v2](../v2/tutorial.md)。日志里只有 Alice=90 时不能发布余额；两条操作都有也仍然不能确定交易已提交。我们需要一条独立的 commit 记录，把“写了哪些操作”和“决定提交”分开。

本篇的事务是一组账户最终值赋值。提交记录前，所有操作只是 pending；看到对应 commit 后才一次更新恢复状态。不变量是一次事务的操作全部可见或全部不可见。金额是否守恒属于转账业务规则，本存储接口允许单账户赋值，事务原子性不自动验证转账业务。

## 1. 从初始状态重建，不信任半成品数据

v0 的数据文件可能只写了一半，甚至是残缺 JSON。恢复时不能先读取它再补日志；没有检查点证明它对应日志哪个位置。本模块保留全部日志，从初始 100/100 重放，data.json 只是可丢弃的派生副本。

replay 用 pending 按事务号收集赋值；commit 出现时更新 state 并删除 pending。日志结束时尚未提交的组忽略。已经提交的事务号不能再次出现；新的写入也不能复用任何曾出现的事务号，包括放弃的事务。否则旧 pending 操作可能被误混入新的请求。这不是请求幂等接口：重复提交编号会报错，重试方应先查询结果或使用额外请求协议。

## 2. 在完整前缀之后继续写入

若日志末尾只剩半帧，直接 append 会让后续新帧成为坏帧的一部分。所以新增提交先解析日志，仅在 decode 判定尾部未完成时截断到 valid_end；完整帧校验失败则停止，不做修复。合法但未提交的完整操作保留，后续新事务用新编号。

commit 在写任何字节前校验编号和变化值，预先编码全部帧，避免编码失败留下半个新事务。操作帧顺序写入后追加 commit 帧，关闭日志后再更新派生数据。此时只有进程可见的写入顺序，没有 fsync，因此本版本还不能宣称断电持久化。

完整检查点如下。保留 framing.py，新增 store.py；旧 prepared.py 仅作上一版对照，不被本版导入。

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

将下面的完整代码保存为 `labs/storage/wal/store.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/wal/store.py -->
```python
import json
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
    def __init__(self, directory: Path) -> None:
        self.log_path = directory / "wal.bin"
        self.data_path = directory / "data.json"
        self.log_path.touch(exist_ok=True)

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
        with self.log_path.open("ab") as log:
            for frame in frames:
                log.write(frame)
        self.data_path.write_text(json.dumps(state))
        return state
```

运行检查：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.wal.framing import encode
from labs.storage.wal.store import Store

with TemporaryDirectory() as directory:
    store = Store(Path(directory))
    assert store.recover() == {"alice": 100, "bob": 100}
    assert store.commit("t1", {"alice": 90, "bob": 110}) == {"alice": 90, "bob": 110}
    with store.log_path.open("ab") as log:
        log.write(encode({"kind": "set", "tx": "abandoned", "key": "alice", "value": 1}))
        log.write(b"abc")
    store.data_path.write_text("broken json")
    assert store.recover() == {"alice": 90, "bob": 110}
    assert store.recover() == store.recover()
    store.commit("t2", {"alice": 80, "bob": 120})
    assert store.recover() == {"alice": 80, "bob": 120}
    before = store.log_path.read_bytes()
    for tx, changes in (("t2", {"alice": 70}), ("t3", {}), ("t3", {"eve": 1})):
        try:
            store.commit(tx, changes)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid transaction accepted")
        assert store.log_path.read_bytes() == before
print("v3 committed groups only")
PY
```

预期 `v3 committed groups only`。未提交组被忽略，损坏数据副本不影响恢复，半帧尾部修整后新的提交仍可识别，非法输入在日志改变之前失败。

重复 recover 不修改日志或余额，所以逻辑恢复幂等。但 commit 过程中数据副本写入失败时，日志可能已经有 commit；调用者收到异常不等于事务必定未提交。下一篇继续解释这种“结果未知”，并把返回成功的位置放在日志持久化之后。
