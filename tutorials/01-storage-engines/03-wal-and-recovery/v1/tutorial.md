# S03 v1：找到日志的完整前缀

前置 [v0](../v0/tutorial.md)。直接覆盖丢失了操作意图，所以我们准备追加日志。但连续写入两段 JSON，进程在第二段中间退出时，读取者怎样知道第一段完整、第二段未完成？单独调用 `json.loads` 无法给整个追加文件划定事务记录边界。

本篇只实现日志帧，不承诺事务恢复或持久化。输入是字典，输出是二进制帧；解码输入完整日志 bytes，输出已完成记录、有效前缀字节数、是否存在未完成尾部。当前全量载入日志，非生产级流式解析器。

## 1. 在负载前写长度，但别盲目信任长度

格式选择为 8 字节头、UTF-8 JSON 负载、4 字节 CRC32。头中存 32 位长度及其按位反码：如果长度字段被单点损坏，两个字段不再匹配，不能误当成“还没写完的巨大记录”。负载上限 1 MiB 避免不合理长度。CRC32 检测负载意外损坏，不用于防恶意篡改，也不是零碰撞证明。

头只有三字节时，我们无法判断它的内容，只报告未完成尾部。如果完整头有效，但后面的负载或校验没有写完，也报告未完成尾部。完整头非法、完整负载校验不符，必须报错，不能跳过这条继续读取。

这依赖一个明确故障模型：单写者按顺序追加，崩溃可能留下尾部前缀。任意位置损坏、长度和反码同时一致地改变，不能保证都被识别为损坏；本实验不是介质修复器。

## 2. 把边界识别做成完整文件

新建 `labs/storage/wal/framing.py`，以下是完整检查点。encode 只编码，不写文件；decode 不修改输入或截断源文件，调用者稍后决定如何处理无效尾部。

循环只在整帧通过校验后更新 position，所以返回的 position 永远指向完整前缀末尾。JSON 解析异常直接传播；即使 CRC 正确，也要求负载是对象。日志语义字段是否合法留到事务层判断，帧层只管理字节边界。

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

运行检查：在第二帧的每一个非完整位置截断，都必须保留第一帧；完整帧被破坏时必须报错。

```bash
uv run python - <<'PY'
from labs.storage.wal.framing import decode, encode

operation = {"kind": "set", "tx": "t1", "key": "alice", "value": 90}
commit = {"kind": "commit", "tx": "t1"}
first, second = encode(operation), encode(commit)
assert decode(first + second) == ([operation, commit], len(first + second), False)
assert decode(b"") == ([], 0, False)
for cut in range(1, len(second)):
    assert decode(first + second[:cut]) == ([operation], len(first), True)
for position, expected in ((0, "header"), (9, "checksum")):
    broken = bytearray(first)
    broken[position] ^= 1
    try:
        decode(bytes(broken))
    except ValueError as error:
        assert expected in str(error)
    else:
        raise AssertionError("complete damaged frame accepted")
try:
    encode({"data": "x" * (1024 * 1024)})
except ValueError:
    pass
else:
    raise AssertionError("oversized frame accepted")
print("v1 frame boundaries ok")
PY
```

预期 `v1 frame boundaries ok`。空日志合法；尾部不完整与完整记录损坏有不同结果。此时即使字典里写着 commit，它也只是普通数据，没有提交含义。

现在我们能区分完整日志前缀与未完成尾部。下一篇先把操作写到日志，再修改数据；这可以重建写入意图，但仍然不能判断一组操作是否得到提交确认。
