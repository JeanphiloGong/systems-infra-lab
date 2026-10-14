# S03 v4：成功确认必须晚于日志同步

前置 [v3](../v3/tutorial.md)。Python 的 write 成功，可能只写进用户态缓冲；flush 把缓冲交给 OS，仍可能只是 OS 页缓存。如果在此时告诉客户“成功”，断电可能让这个承诺无法兑现。

本篇限定本地 POSIX 文件系统、单写者、目录由调用者事先创建且其存在已持久化。我们按 fsync 合同安排顺序，不在普通进程实验里声称真的拔过电。文件系统、挂载选项、设备写缓存和硬件是否遵守持久化请求仍然影响真实保证。

## 1. 明确三个不同的完成点

提交序列应是：写操作帧，写提交帧，flush，fsync 日志，更新可丢弃数据副本，返回成功。只有日志是恢复权威，因此不要求 data.json 在确认前 fsync；即使它丢失，完整日志仍能重建。

新建日志还有另一个缺口：文件内容 fsync 不等于它的目录项也持久化。初始化时创建并同步空日志，再 fsync 所在目录。每次打开 Store 都同步目录，以覆盖上次创建后尚未同步目录就退出的情况。调用者创建目录本身的父目录持久化不在 Store 内负责。

修剪未完成尾帧也要 flush/fsync 后再继续追加，避免把已知不完整边界带入新提交。完整帧损坏仍然直接报错。

## 2. 给成功之前的动作留下可检查轨迹

给 Store 增加可选 event 回调，它接收刚完成动作的名称。回调是实验探针，不参与业务恢复决策；下一篇用它在精确边界退出。没有回调时不做额外 I/O。

日志 fsync 失败必须抛异常，不走到 before_ack。反过来，未收到成功并不等于事务没有提交：fsync 已完成后进程也可能在返回前退出。恢复看到完整 commit 时应保留事务。应用需要处理结果未知，而不是自动再扣一次款。

以下完整检查点更新 store.py，framing.py 不变。before_ack 表示即将返回，并不是客户已经收到响应。


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

<!-- checkpoint: labs/storage/wal/store.py -->
```python
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
```

运行轨迹与失败检查。失败注入只替换 fsync 的一次调用，目的在于验证程序不错误确认，不用它模拟真实断电：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from labs.storage.wal.store import Store

with TemporaryDirectory() as directory:
    events = []
    store = Store(Path(directory), event=events.append)
    assert events == ["wal_created", "directory_synced"]
    store.commit("t1", {"alice": 90, "bob": 110})
    assert events[2:] == [
        "operation_1_written", "operation_2_written", "commit_written",
        "wal_flushed", "wal_synced", "data_written", "before_ack",
    ]
    events.clear()
    with patch("labs.storage.wal.store.os.fsync", side_effect=OSError("injected")):
        try:
            store.commit("t2", {"alice": 80, "bob": 120})
        except OSError:
            pass
        else:
            raise AssertionError("fsync failure acknowledged")
    assert "wal_flushed" in events
    assert "wal_synced" not in events
    assert "before_ack" not in events
    assert store.recover() == {"alice": 80, "bob": 120}
print("v4 sync before acknowledgement")
PY
```

预期 `v4 sync before acknowledgement`。第二次 fsync 抛错，但日志已 flush，当前 OS 内仍能读取完整提交，所以 recover 返回 80/120。这正好展示“调用报错，但可能已提交”的情况，而非测试矛盾。数据副本写入失败同样可能发生在日志已持久化之后。

现在程序的确认顺序符合声明的持久化模型，轨迹证明分支顺序，尚未通过真实退出验证每个边界。下一篇用独立子进程完成这个故障矩阵。
