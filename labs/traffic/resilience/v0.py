from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def call(operation: Callable[[], T], max_attempts: int = 3) -> tuple[T, int]:
    """Retry every failure immediately and return the result and attempt count."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    for attempt in range(1, max_attempts + 1):
        try:
            return operation(), attempt
        except Exception:
            if attempt == max_attempts:
                raise
    raise AssertionError("unreachable")


if __name__ == "__main__":
    attempts = 0

    def dependency() -> str:
        global attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("temporary failure")
        return "ok"

    print(call(dependency))
