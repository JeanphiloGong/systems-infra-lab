# S04 v1：用位数组给出单向可靠的否定

前置 [v0](../v0/tutorial.md)。三个文件的缺失查询都要读取。如果把文件里所有键放进精确集合，可以避免负查询，但索引的内存会随键长度增长。Bloom Filter 只保留被键设置过的位，牺牲肯定回答的精确性来压缩内存。

本篇模型只有位数组、稳定哈希位置、add 和 might_contain。没有文件查询集成，也没有删除。所有已插入键都必须返回 True；未插入键可能因为其他键的位发生碰撞而返回 True。

## 1. 为什么碰撞不能造成假阴性

假设一条键设置第 1、4、7 位。插入其他键只会把更多位设成 1，不会清零，因此原键再来时三个位置仍都为 1。查询只要发现任何一位为零就能证明没插入过；全部为一却只能说明“可能存在”。

直接清掉某键的位会破坏其他共享这些位的键，所以普通 Bloom Filter 不能直接删除。这个不变量比某一次测量的假阳性率更重要。

## 2. 位位置必须在重启后保持一致

Python 字符串 hash 默认带进程随机种子，不能作为可重放的映射。我们明确把字符串编码为 UTF-8，使用 BLAKE2b 的 16 字节摘要，前后八字节各按小端解释为整数，然后用 (first+i*second)%bits 派生位置。

second 设为奇数，在位数是二的幂时避免步长只访问一部分位；对任意位数不保证互质，也不保证这些位置完全独立。因此本例是稳定的双哈希近似，不把后续概率公式当精确等式。

一个字节存八位，位置 p 的字节索引是 p//8，掩码是 1<<(p%8)。add 用按位或设置，查询用按位与检测。末尾不足八位仍分配一个完整字节；bytes_used 只报告位数组载荷，不包括 Python 对象、临时摘要和列表内存。

以下新建 labs/storage/bloom/filter.py。参数必须为正；重复 add 不改变已设置的位。

<!-- checkpoint: labs/storage/bloom/filter.py -->
```python
from __future__ import annotations

from hashlib import blake2b


class BloomFilter:
    def __init__(self, bits: int, hashes: int) -> None:
        if bits < 1 or hashes < 1:
            raise ValueError("bits and hashes must be positive")
        self.bits = bits
        self.hashes = hashes
        self.array = bytearray((bits + 7) // 8)

    def _positions(self, key: str) -> list[int]:
        digest = blake2b(key.encode("utf-8"), digest_size=16).digest()
        first = int.from_bytes(digest[:8], "little")
        second = int.from_bytes(digest[8:], "little") | 1
        return [(first + index * second) % self.bits for index in range(self.hashes)]

    def add(self, key: str) -> None:
        for position in self._positions(key):
            self.array[position // 8] |= 1 << (position % 8)

    def might_contain(self, key: str) -> bool:
        return all(self.array[position // 8] & (1 << (position % 8)) for position in self._positions(key))

    @property
    def bytes_used(self) -> int:
        return len(self.array)
```

运行可重复检查，并强制制造假阳性以理解 True 的含义：

```bash
uv run python - <<'PY'
from labs.storage.bloom.filter import BloomFilter

bloom = BloomFilter(1024, 4)
keys = ["a", "b", "订单-1", ""]
for key in keys:
    bloom.add(key)
assert all(bloom.might_contain(key) for key in keys)
before = bytes(bloom.array)
bloom.add("a")
assert bytes(bloom.array) == before
assert bloom.bytes_used == 128
assert BloomFilter(9, 2).bytes_used == 2
saturated = BloomFilter(1, 1)
saturated.add("present")
assert saturated.might_contain("absent")
for bits, hashes in ((0, 1), (8, 0)):
    try:
        BloomFilter(bits, hashes)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid size accepted")
print("v1: no false negatives; forced false positive observed")
PY
```

只有一位时，插入后任意查询都是 True，正好说明假阳性不是实现异常。下一篇改变位数、哈希次数、插入量，测量这个代价，而不是只找一个“看起来很低”的概率。

