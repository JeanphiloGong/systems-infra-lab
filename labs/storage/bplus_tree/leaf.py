from bisect import bisect_left
from typing import Generic, TypeVar

Value = TypeVar("Value")


class LeafPage(Generic[Value]):
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.items: list[tuple[int, Value]] = []

    def get(self, key: int) -> Value | None:
        position = bisect_left([item[0] for item in self.items], key)
        if position == len(self.items) or self.items[position][0] != key:
            return None
        return self.items[position][1]

    def insert(self, key: int, value: Value) -> int:
        keys = [item[0] for item in self.items]
        position = bisect_left(keys, key)
        if position < len(self.items) and self.items[position][0] == key:
            self.items[position] = (key, value)
            return 0
        if len(self.items) == self.capacity:
            raise OverflowError("leaf page is full")
        moved = len(self.items) - position
        self.items.insert(position, (key, value))
        return moved
