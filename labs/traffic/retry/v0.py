from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def call(operation: Callable[[], T], max_attempts: int = 3) -> tuple[T, int]:
    for attempt in range(1, max_attempts + 1):
        try:
            return operation(), attempt
        except Exception:
            if attempt == max_attempts:
                raise
    raise AssertionError("unreachable")


if __name__ == "__main__":
    print(call(lambda: "ok"))
