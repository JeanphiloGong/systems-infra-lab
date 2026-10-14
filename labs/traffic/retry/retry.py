from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Callable, TypeVar


class RetryableError(Exception):
    pass


class PermanentError(Exception):
    pass


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    deadline: float = 1.0
    base_delay: float = 0.01
    jitter: float = 0.0


def call(operation: Callable[[], T], policy: RetryPolicy, sleep: Callable[[float], None]) -> tuple[T, int]:
    if policy.max_attempts < 1 or policy.deadline < 0 or policy.base_delay < 0 or policy.jitter < 0:
        raise ValueError("invalid retry policy")
    elapsed = 0.0
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return operation(), attempt
        except PermanentError:
            raise
        except RetryableError:
            if attempt == policy.max_attempts:
                raise
            delay = policy.base_delay * (2 ** (attempt - 1))
            delay += random.uniform(0, policy.jitter)
            if elapsed + delay >= policy.deadline:
                raise TimeoutError("retry deadline exceeded")
            sleep(delay)
            elapsed += delay
    raise AssertionError("unreachable")


def main() -> None:
    print(call(lambda: "ok", RetryPolicy(), lambda _: None))


if __name__ == "__main__":
    main()
