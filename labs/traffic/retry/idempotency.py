from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


@dataclass
class OperationStore(Generic[T]):
    values: dict[str, T]

    def __init__(self) -> None:
        self.values = {}

    def run(self, operation_id: str, operation: Callable[[], T]) -> T:
        if not operation_id:
            raise ValueError("operation_id is required")
        if operation_id not in self.values:
            self.values[operation_id] = operation()
        return self.values[operation_id]


def main() -> None:
    store: OperationStore[str] = OperationStore()
    print(store.run("payment-1", lambda: "charged"))
    print(store.run("payment-1", lambda: "charged-again"))


if __name__ == "__main__":
    main()
