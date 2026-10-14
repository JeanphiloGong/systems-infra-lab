from __future__ import annotations

from typing import Callable, TypeVar

class RetryableError(Exception): pass
class PermanentError(Exception): pass
T = TypeVar("T")

def call(operation: Callable[[], T], max_attempts: int = 3, deadline: float = 1.0) -> tuple[T, int]:
    if max_attempts < 1 or deadline < 0: raise ValueError("invalid policy")
    elapsed = 0.0
    for attempt in range(1, max_attempts + 1):
        try: return operation(), attempt
        except PermanentError: raise
        except RetryableError:
            if attempt == max_attempts or elapsed >= deadline: raise TimeoutError("retry deadline exceeded")
    raise AssertionError("unreachable")

if __name__ == "__main__": print(call(lambda: "ok"))
