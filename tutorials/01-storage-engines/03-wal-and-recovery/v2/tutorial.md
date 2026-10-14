# S03 v2：先记操作，仍不能把它叫作提交

前置 [v1](../v1/tutorial.md)。v0 只留下被覆盖的数据，没有可追踪意图。现在我们先把“将 Alice 设为 90，将 Bob 设为 110”写到追加日志，再改变数据文件。即使数据写入没有发生，也能从日志重建候选结果。

但存在一个关键问题：日志里的操作究竟是已经提交的交易，还是写到一半被放弃的尝试？本篇故意保留这个缺口，不把“能够重放”宣传为“已经支持事务恢复”。

## 1. 记录结果赋值，而不是再次扣款

如果日志记录“扣 10”，恢复两次可能从 100 变 90 再变 80。我们选择 after-image 赋值：记录余额应为 90。重放同一赋值多次，逻辑结果不变。这个选择只解决重放幂等性，还没有隔离或并发语义。

日志先写 Alice、再写 Bob。读取时从已知初始状态开始应用完整操作帧；返回候选字典以及见过的事务编号集合。所有编号都标为 pending，因为没有任何提交帧。只有第一条操作完整时，候选可能是 90/100；调用者绝不能把这个候选暴露为已提交余额。

## 2. 用显式分支观察日志先于数据

新建 prepared.py。prepare 的 apply=False 表示停在日志关闭之后、数据写入之前，方便检查状态；它不是模拟断电。apply=True 才写候选数据。日志使用 xb，新实验必须用新路径，避免不经意覆盖前一次日志。文件关闭把 Python 缓冲交给 OS，但仍没有 fsync。

inspect_pending 只读取日志，不改写数据。它校验操作类型、事务编号、账户名与非负整数金额；非法日志抛错。完整文件如下，包含它依赖的 v1 编解码器：

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

<!-- checkpoint: labs/storage/wal/prepared.py -->
```python
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
```

运行两个独立目录状态，分别观察只记日志与日志后写数据：

```bash
uv run python - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.wal.prepared import prepare, inspect_pending
from labs.storage.wal.framing import decode, encode

with TemporaryDirectory() as directory:
    root = Path(directory)
    data, log = root / "data.json", root / "wal.bin"
    initial = {"alice": 100, "bob": 100}
    data.write_text(json.dumps(initial))
    prepare(data, log, apply=False)
    candidate, pending = inspect_pending(log)
    assert candidate == {"alice": 90, "bob": 110}
    assert pending == {"t1"}
    assert json.loads(data.read_text()) == initial
    assert inspect_pending(log) == (candidate, pending)
    records, _, _ = decode(log.read_bytes())
    log.write_bytes(encode(records[0]))
    assert inspect_pending(log) == ({"alice": 90, "bob": 100}, {"t1"})
    second_log = root / "second.bin"
    prepare(data, second_log, apply=True)
    assert json.loads(data.read_text()) == candidate
    assert inspect_pending(second_log)[1] == {"t1"}
print("v2 intent is present, commit is unknown")
PY
```

预期 `v2 intent is present, commit is unknown`。重复读取候选结果不累计扣款；只有第一条记录也能解码，但总额不守恒。因此“有日志”仍不够，必须把提交作为独立事实记录。

本版已经满足日志写入先于数据改写的程序顺序，却没有承诺 WAL 的持久化顺序：OS 仍可能在断电时丢失未 fsync 的日志。下一篇先补上提交规则，之后再处理 flush/fsync 与成功确认顺序。
