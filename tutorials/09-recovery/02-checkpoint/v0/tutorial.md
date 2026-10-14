# A02 v0：先量出完整日志恢复的代价

账户服务每次转账都已经得到确认，进程却可能在下一次请求前退出。重新启动时，
我们不能只看最后一个内存余额；必须从已发布的持久记录恢复。这个版本故意不做
快照，把问题压缩成两个账户和连续的不可变事务段：每段有两个 `set` 和一个
`commit`，并且总余额保持 200。

先写一笔转账，再重新打开目录。读者看到的第一个压力是历史长度：恢复 10 笔要
读取 10 个段，恢复 1000 笔就要读取 1000 个段。`recover` 返回实际事务数和字节数，
所以输出不是把输入规模重新打印一遍。

每个段先写临时文件，刷新并同步，再原子改名并同步目录。恢复只认 `*.wal`；
临时文件可能是崩溃残留，不能当作已提交事务。已发布段缺少一个编号或 CRC 不对时，
恢复必须失败，而不是返回一个看似合理的部分余额。

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

这里的 `framing.py` 是 S03 已验证的长度、互补长度和 CRC 编码；A02 只决定如何
组织完整事务段和恢复位置。运行 v0 前，先把依赖源码提取到临时目录，或在仓库根目录执行：

```bash
uv run pytest tests/recovery/checkpoint/test_baseline.py -q
```

四项测试分别覆盖正常读取、未发布临时文件、缺段、截断、CRC、非法输入和重复编号。
冻结这个检查点后仍然有一个清楚的缺口：每次重启都要重新解码整个前缀。下一版会
在暂停写入时保存与状态严格对应的位置，并只重放快照之后的尾部。

边界要保持诚实：这里的目录同步和进程重启实验不是断电证明，事务段格式也不是
生产数据库的完整检查点协议。A02 的后续版本会先处理发布顺序，再处理备用快照。
