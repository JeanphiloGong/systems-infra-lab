import random
from math import ceil
from time import perf_counter_ns

from labs.storage.pages.paged import PageReader
from labs.storage.pages.records import RECORD


def workloads(count: int, seed: int) -> tuple[list[int], list[int]]:
    if count < 0:
        raise ValueError("count must be nonnegative")
    sequential = list(range(count))
    shuffled = sequential.copy()
    random.Random(seed).shuffle(shuffled)
    return sequential, shuffled


def measure(reader: PageReader, keys: list[int]) -> dict[str, int]:
    if not keys:
        raise ValueError("empty workload")
    before_requests = reader.page_requests
    before_reads = reader.file_reads
    before_bytes = reader.bytes_read
    pages: set[int] = set()
    durations: list[int] = []
    checksum = 0
    for key in keys:
        start = perf_counter_ns()
        value = reader.get(key)
        durations.append(perf_counter_ns() - start)
        if value is None:
            raise ValueError("workload requested missing record")
        checksum += value
        first = key * RECORD.size // reader.page_size
        last = ((key + 1) * RECORD.size - 1) // reader.page_size
        pages.update(range(first, last + 1))
    durations.sort()
    return {
        "requests": len(keys),
        "checksum": checksum,
        "page_requests": reader.page_requests - before_requests,
        "file_reads": reader.file_reads - before_reads,
        "bytes_read": reader.bytes_read - before_bytes,
        "unique_pages": len(pages),
        "p50_ns": durations[ceil(len(durations) * 0.50) - 1],
        "p95_ns": durations[ceil(len(durations) * 0.95) - 1],
        "max_ns": durations[-1],
    }
