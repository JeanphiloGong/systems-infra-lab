from collections import OrderedDict
from pathlib import Path

from labs.storage.pages.records import RECORD


class PageReader:
    def __init__(self, path: Path, page_size: int = 4096, capacity: int = 0) -> None:
        if page_size < 1:
            raise ValueError("page_size must be positive")
        if capacity < 0:
            raise ValueError("capacity must be nonnegative")
        self.capacity = capacity
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.path = path
        self.page_size = page_size
        self.size = path.stat().st_size
        if self.size % RECORD.size:
            raise ValueError("truncated record")
        self.bytes_read = 0
        self.page_requests = 0
        self.file_reads = 0
        self.pages_seen: set[int] = set()

    def read_page(self, page_id: int) -> bytes:
        if page_id < 0 or page_id * self.page_size >= self.size:
            raise ValueError("page outside file")
        self.page_requests += 1
        self.pages_seen.add(page_id)
        if page_id in self.cache:
            self.cache.move_to_end(page_id)
            return self.cache[page_id]
        with self.path.open("rb") as source:
            source.seek(page_id * self.page_size)
            data = source.read(self.page_size)
        self.file_reads += 1
        self.bytes_read += len(data)
        expected = min(self.page_size, self.size - page_id * self.page_size)
        if len(data) != expected:
            raise ValueError("file changed during experiment")
        if self.capacity:
            if len(self.cache) == self.capacity:
                self.cache.popitem(last=False)
            self.cache[page_id] = data
        return data

    def get(self, key: int) -> int | None:
        if key < 0 or key >= self.size // RECORD.size:
            return None
        start = key * RECORD.size
        stop = start + RECORD.size
        data = bytearray()
        for page_id in range(start // self.page_size, (stop - 1) // self.page_size + 1):
            page = self.read_page(page_id)
            base = page_id * self.page_size
            data.extend(page[max(start - base, 0):min(stop - base, len(page))])
        stored_key, value = RECORD.unpack(data)
        if stored_key != key:
            raise ValueError("key does not match slot")
        return value
