from __future__ import annotations

import random
from typing import Callable, TypeVar

class RetryableError(Exception): pass
class PermanentError(Exception): pass
T = TypeVar("T")

def call(operation: Callable[[], T], max_attempts: int = 3, deadline: float = 1.0, base_delay: float = .01, jitter: float = 0.0, sleep: Callable[[float], None] = lambda _: None) -> tuple[T, int]:
    if max_attempts < 1 or deadline < 0 or base_delay < 0 or jitter < 0: raise ValueError("invalid policy")
    elapsed = 0.0
    for attempt in range(1, max_attempts + 1):
        try: return operation(), attempt
        except PermanentError: raise
        except RetryableError:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, jitter)
            if attempt == max_attempts or elapsed + delay >= deadline: raise TimeoutError("retry deadline exceeded")
            sleep(delay); elapsed += delay
    raise AssertionError("unreachable")

if __name__ == "__main__": print(call(lambda: "ok"))
