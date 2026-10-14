from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TypeVar


class RetryableError(Exception):
    pass


class PermanentError(Exception):
    pass


class BudgetExhausted(Exception):
    pass


@dataclass
class Budget:
    remaining: int

    def __post_init__(self) -> None:
        if self.remaining < 0:
            raise ValueError("negative budget")

    def consume(self) -> None:
        if self.remaining == 0:
            raise BudgetExhausted("leaf attempt budget exhausted")
        self.remaining -= 1


T = TypeVar("T")


def call_layers(
    operation: Callable[[], T], layers: int = 3, attempts: int = 3,
    budget: Budget | None = None, deadline: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
) -> T:
    if layers < 1 or attempts < 1 or deadline < 0:
        raise ValueError("invalid retry policy")
    expires = clock() + deadline

    def check_time() -> None:
        if clock() >= expires:
            raise TimeoutError("shared deadline exceeded")

    def invoke(depth: int) -> T:
        check_time()
        if depth == 0:
            if budget is not None:
                budget.consume()
            check_time()
            try:
                result = operation()
            except RetryableError:
                check_time()
                raise
            check_time()
            return result
        for attempt in range(attempts):
            try:
                return invoke(depth - 1)
            except RetryableError:
                check_time()
                if attempt == attempts - 1:
                    raise
        raise AssertionError("unreachable")

    return invoke(layers)


def amplification(limit: int | None) -> int:
    calls = 0

    def unavailable() -> None:
        nonlocal calls
        calls += 1
        raise RetryableError("dependency unavailable")

    try:
        call_layers(unavailable, budget=None if limit is None else Budget(limit))
    except (RetryableError, BudgetExhausted):
        pass
    return calls


if __name__ == "__main__":
    print(amplification(None), amplification(10))
