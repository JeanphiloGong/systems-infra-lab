# S03 v5：在每个边界退出，再由新进程恢复

前置 [v4](../v4/tutorial.md)。轨迹说明 fsync 在确认之前，但没有真的让进程在这些位置消失。现在给每个边界一个名字，让子进程在对应探针调用 os._exit(73)，随后启动全新的 Python 进程恢复两次。

本实验覆盖程序暴露的写入、flush、fsync、数据副本与确认边界，不声称覆盖文件系统内部所有指令。帧内部每个字节的截断由 v1 测试覆盖；真实断电与设备故障仍不在测试环境内。

## 1. 把确认与进程存活分开观察

worker 调用 commit 返回后打印并 flush 一行 ACK，父进程据此观察成功。after_ack 探针在这之后退出，证明“客户端观察到成功后服务进程退出”仍可恢复。before_ack 探针发生在函数返回前，不应有 ACK。

operation_N_written 与 commit_written 只表示 Python 缓冲写入返回；是否已到 OS 不作假设。wal_flushed 后针对进程退出，完整日志在 OS 中可见；针对断电仍须 wal_synced。本实验对早期边界允许事务不存在或完整存在，绝不允许只有 Alice 改了。

已有提交还必须受保护：先提交 t0=95/105，再让 t1=90/110 在每个边界退出。恢复只能是旧值或新值，不能回到 100/100，也不能混合两次事务。wal_created 只在全新日志出现，因此已有提交矩阵从 directory_synced 开始。

## 2. 加入独立的故障执行入口

还有一个需要已有不完整尾帧才会触发的边界：tail_repaired。它在截断无效尾并 fsync 之后发生。单独准备已提交 t0 与三个残片字节，修尾后立刻退出，必须保住 t0；随后新的进程仍应能够追加提交。

新增 crash_worker.py，核心 Store 与帧格式不变。所有实验使用临时目录；os._exit 只终止 worker。恢复操作仅从日志计算状态，不信任 data.json，也不向日志追加内容。

完整检查点包括以下三个文件：

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

将下面的完整代码保存为 `labs/storage/wal/crash_worker.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/storage/wal/crash_worker.py -->
```python
import argparse
import json
import os
from pathlib import Path

from labs.storage.wal.store import Store


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("action", choices=("write", "recover"))
    parser.add_argument("--crash-at", default="")
    args = parser.parse_args()

    def event(name: str) -> None:
        if name == args.crash_at:
            os._exit(73)

    store = Store(args.directory, event=event)
    if args.action == "recover":
        print(json.dumps(store.recover(), sort_keys=True))
        return
    store.commit("t1", {"alice": 90, "bob": 110})
    print("ACK", flush=True)
    event("after_ack")


if __name__ == "__main__":
    main()
```

下面的检查是真实故障矩阵，每个边界都创建独立目录并重启恢复进程。通常数秒结束：

```bash
uv run python - <<'PY'
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from labs.storage.wal.store import Store

points = [
    "wal_created", "directory_synced", "operation_1_written", "operation_2_written",
    "commit_written", "wal_flushed", "wal_synced", "data_written", "before_ack", "after_ack",
]
committed = {"alice": 90, "bob": 110}
for prior in (False, True):
    for point in points[int(prior):]:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            previous = {"alice": 100, "bob": 100}
            if prior:
                previous = {"alice": 95, "bob": 105}
                Store(root).commit("t0", previous)
            command = [sys.executable, "-m", "labs.storage.wal.crash_worker", directory]
            result = subprocess.run(
                command + ["write", "--crash-at", point],
                text=True, capture_output=True, check=False,
            )
            assert result.returncode == 73, result.stderr
            assert ("ACK" in result.stdout) == (point == "after_ack")
            states = []
            for _ in range(2):
                recovered = subprocess.run(
                    command + ["recover"], text=True, capture_output=True, check=True,
                )
                states.append(json.loads(recovered.stdout))
            assert states[0] == states[1]
            assert states[0] in (previous, committed)
            if point in ("wal_flushed", "wal_synced", "data_written", "before_ack", "after_ack"):
                assert states[0] == committed
            print("prior=", prior, point, states[0])
with TemporaryDirectory() as directory:
    root = Path(directory)
    previous = {"alice": 95, "bob": 105}
    store = Store(root)
    store.commit("t0", previous)
    with store.log_path.open("ab") as log:
        log.write(b"abc")
    command = [sys.executable, "-m", "labs.storage.wal.crash_worker", directory]
    result = subprocess.run(command + ["write", "--crash-at", "tail_repaired"],
                            text=True, capture_output=True, check=False)
    assert result.returncode == 73 and "ACK" not in result.stdout
    for _ in range(2):
        result = subprocess.run(command + ["recover"], text=True, capture_output=True, check=True)
        assert json.loads(result.stdout) == previous
    result = subprocess.run(command + ["write"], text=True, capture_output=True, check=True)
    assert "ACK" in result.stdout
    result = subprocess.run(command + ["recover"], text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == committed
print("v5: 20 crash cases recovered atomically")
PY
```

预期输出 19 条矩阵恢复状态和 `v5: 20 crash cases recovered atomically`。最后一个修尾故障单独检查，不打印状态行。早期边界只断言原子性，避免把 Python 缓冲行为当持久化合同。后续边界在这个进程退出模型下必须恢复新值。重复恢复相同，体现 after-image 重放的幂等性。

可选执行 [参考分支检查](../../../../docs/reference-checks.md) 检查最终代码；可选执行 [参考分支检查](../../../../docs/reference-checks.md) 在独立临时目录重放六篇正文。完整帧损坏会报错而不是静默丢弃，未完成尾帧不会被当成提交。

## 这个恢复模型仍然缺少什么

日志永不截断，恢复成本随历史增长；生产系统需要检查点与日志保留协议，本项目在 A02 继续。单写者约定没有通过跨进程锁强制实现，并发运行两个 writer 会破坏合同。data.json 是可丢弃副本，外部读取它可能看到部分写入；正式读接口必须用 recover 或后续一致的内存状态。

调用方遇到未确认结果仍要查询事务结果，不能随便换事务号重复转账。这里实现的是简化 redo 事务日志，既不是 ARIES，也不是 exactly-once 业务处理，更没有用进程退出测试证明真实断电恢复。

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/storage/wal/ -q
uv run python tests/storage/wal/replay_s03.py
```

</details>
