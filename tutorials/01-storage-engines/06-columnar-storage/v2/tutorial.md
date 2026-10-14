# S06 v2：地区字典：把重复字符串换成短代码

前置 v1。300 行的地区列只有 east、west 和缺失值，却按每行12字节占3600字节。列布局让相同值相邻于同一文件；我们现在单独压缩地区，不改变金额的语义。

## 1. 给重复地区分配代码

字典保存每个不同地区一次，每行只存一个16位无符号代码。code0专门表示None，east和west按首次出现顺序获得1和2。代码是位置，不是地区值本身，必须和对应字典一起保存。

编码输出两个bytes：UTF-8 JSON字典和小端uint16代码流。选择标准JSON保留非ASCII地区，避免手写字符串分隔协议。容量最多65536个字典项，包含None；继续出现新值时抛错。字典越大越可能抵消收益，所以编码不保证所有数据都压缩。

## 2. 解码必须守住缺失值和边界

None不应变成空字符串。解码要求字典首项为None、其余项为字符串；代码流长度必须是2的倍数，任何越界代码拒绝。没有压缩金额、编号和备注，也没有使用字典顺序决定地区排序。

以下是新增dictionary.py的完整检查点。此模块只处理地区值列表，不依赖其他源码；v1列扫描器保持不变。

<!-- checkpoint: labs/storage/columnar/dictionary.py -->
```python
import json
from struct import Struct

CODE = Struct("<H")


def encode_regions(values: list[str | None]) -> tuple[bytes, bytes]:
    dictionary: list[str | None] = [None]
    positions: dict[str | None, int] = {None: 0}
    output = bytearray()
    for value in values:
        if value is not None and not isinstance(value, str):
            raise ValueError("region must be text or None")
        if value not in positions:
            if len(dictionary) == 65536:
                raise ValueError("too many dictionary values")
            positions[value] = len(dictionary)
            dictionary.append(value)
        output.extend(CODE.pack(positions[value]))
    return json.dumps(dictionary, ensure_ascii=False).encode("utf-8"), bytes(output)


def decode_regions(dictionary_bytes: bytes, codes: bytes) -> list[str | None]:
    dictionary = json.loads(dictionary_bytes)
    if not isinstance(dictionary, list) or not dictionary or dictionary[0] is not None:
        raise ValueError("dictionary must reserve zero for None")
    if any(not isinstance(value, str) for value in dictionary[1:]):
        raise ValueError("invalid dictionary value")
    if len(codes) % CODE.size:
        raise ValueError("partial dictionary code")
    result: list[str | None] = []
    for offset in range(0, len(codes), CODE.size):
        index = CODE.unpack_from(codes, offset)[0]
        if index >= len(dictionary):
            raise ValueError("dictionary code outside table")
        result.append(dictionary[index])
    return result
```

```bash
uv run python - <<'PY'
from labs.storage.columnar.dictionary import encode_regions, decode_regions

values = ["east", "west", None] * 100
dictionary, codes = encode_regions(values)
assert decode_regions(dictionary, codes) == values
assert len(codes) == 600
assert len(dictionary) + len(codes) < len(values) * 12
assert decode_regions(*encode_regions([])) == []
assert decode_regions(*encode_regions(["订单", None, "订单"])) == ["订单", None, "订单"]
for invalid in (b"\xff\xff", b"x"):
    try:
        decode_regions(dictionary, invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("bad dictionary code accepted")
print("plain_region_bytes", len(values) * 12)
print("dictionary_bytes", len(dictionary), "code_bytes", len(codes))
print("v2: decoded values and missing values preserved")
PY
```

预期原列3600字节，代码600字节，另加打印出的短字典。计算必须包含字典，不能只拿600与3600比较。这个数字是编码载荷，不含Python对象开销。

尝试改成300个不同地区，观察字典开销增长。字典只是编码选择，不等于向量化执行或通用压缩格式。下一篇增加批次统计，跳过不可能匹配的金额范围；为了隔离变量，批次实验继续使用v1未编码的地区列。
