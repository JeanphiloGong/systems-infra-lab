from pathlib import Path

from labs.storage.bloom.filter import BloomFilter
from labs.storage.lsm.sstable import SSTable


class ImmutableTable:
    def __init__(self, path: Path, bits: int = 1024, hashes: int = 4) -> None:
        self.path = path
        self.table = SSTable(path)
        self.build_reads = 0
        self.query_reads = 0
        self.filter = BloomFilter(bits, hashes)
        self.build_reads += 1
        for key, _ in self.table.items():
            self.filter.add(key)

    def query(self, key: str) -> tuple[str | None, int]:
        if not self.filter.might_contain(key):
            return None, 0
        self.query_reads += 1
        return self.table.get(key), 1
