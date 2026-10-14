from __future__ import annotations

from hashlib import blake2b
import math


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


def theoretical_false_positive_rate(bits: int, hashes: int, inserted: int) -> float:
    if bits < 1 or hashes < 1 or inserted < 0:
        raise ValueError("positive bits/hashes and nonnegative inserted required")
    return (1 - math.exp(-hashes * inserted / bits)) ** hashes
