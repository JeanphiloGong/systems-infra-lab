from bisect import bisect_left
from typing import Generic, TypeVar

Value = TypeVar("Value")


class OrderedIndex(Generic[Value]):
    def __init__(self) -> None:
        self.keys: list[int] = []
        self.values: list[Value] = []

    def get(self, key: int) -> Value | None:
        position = bisect_left(self.keys, key)
        if position == len(self.keys) or self.keys[position] != key:
            return None
        return self.values[position]

    def insert(self, key: int, value: Value) -> int:
        position = bisect_left(self.keys, key)
        if position < len(self.keys) and self.keys[position] == key:
            self.values[position] = value
            return 0
        self.keys.insert(position, key)
        self.values.insert(position, value)
        return len(self.keys) - position - 1
