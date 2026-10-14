from __future__ import annotations

import random
import time
from typing import Callable, TypeVar



class RetryableError(Exception):
    """A failure that may succeed on a later attempt."""


class PermanentError(Exception):
    """A failure that must be returned without retrying."""

T = TypeVar("T")


def call(
    operation: Callable[[], T],
    max_attempts: int = 3,
    deadline: float = 1.0,
    base_delay: float = 0.01,
    jitter: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[T, int]:
    if max_attempts < 1 or deadline < 0 or base_delay < 0 or jitter < 0:
        raise ValueError("invalid retry policy")
    source = rng or random
    expires = clock() + deadline
    for attempt in range(1, max_attempts + 1):
        if clock() >= expires:
            raise TimeoutError("retry deadline exceeded")
        try:
            result = operation()
        except PermanentError:
            raise
        except RetryableError:
            if clock() >= expires:
                raise TimeoutError("retry deadline exceeded")
            if attempt == max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1)) + source.uniform(0, jitter)
            if clock() + delay >= expires:
                raise TimeoutError("retry deadline exceeded")
            sleep(delay)
        else:
            if clock() >= expires:
                raise TimeoutError("operation completed after deadline")
            return result, attempt
    raise AssertionError("unreachable")


if __name__ == "__main__":
    print(call(lambda: "ok", rng=random.Random(7)))
