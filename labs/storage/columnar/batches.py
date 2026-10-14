from dataclasses import dataclass
from pathlib import Path

from labs.storage.columnar.columns import AMOUNT, write_columns
from labs.storage.columnar.rows import Order, unpack_text


@dataclass(frozen=True)
class Batch:
    directory: Path
    count: int
    minimum: int
    maximum: int


def write_batches(directory: Path, orders: list[Order], batch_size: int) -> tuple[Batch, ...]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    batches: list[Batch] = []
    for start in range(0, len(orders), batch_size):
        group = orders[start:start + batch_size]
        target = directory / f"batch-{start}"
        target.mkdir()
        write_columns(target, group)
        batches.append(Batch(target, len(group), min(order.amount for order in group), max(order.amount for order in group)))
    return tuple(batches)


def scan_batches(batches: tuple[Batch, ...], region: str | None, low: int, high: int) -> tuple[int, int, int]:
    total = bytes_read = batches_read = 0
    if low > high:
        return total, bytes_read, batches_read
    for batch in batches:
        if batch.maximum < low or batch.minimum > high:
            continue
        regions = (batch.directory / "region.bin").read_bytes()
        amounts = (batch.directory / "amount.bin").read_bytes()
        if len(regions) != batch.count * 12 or len(amounts) != batch.count * AMOUNT.size:
            raise ValueError("batch data changed")
        bytes_read += len(regions) + len(amounts)
        batches_read += 1
        for index in range(batch.count):
            amount = AMOUNT.unpack_from(amounts, index * AMOUNT.size)[0]
            if low <= amount <= high and unpack_text(regions[index * 12:(index + 1) * 12]) == region:
                total += amount
    return total, bytes_read, batches_read
