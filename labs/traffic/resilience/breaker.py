from __future__ import annotations

from enum import Enum


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failures: int = 2) -> None:
        if failures < 1:
            raise ValueError("failures must be positive")
        self.failures = failures
        self.failed = 0
        self.state = State.CLOSED
        self.probe_in_flight = False

    def allow(self) -> bool:
        if self.state is State.OPEN:
            return False
        if self.state is State.HALF_OPEN:
            if self.probe_in_flight:
                return False
            self.probe_in_flight = True
        return True

    def success(self) -> None:
        self.failed = 0
        self.probe_in_flight = False
        self.state = State.CLOSED

    def failure(self) -> None:
        self.probe_in_flight = False
        if self.state is State.HALF_OPEN:
            self.state = State.OPEN
        elif self.state is State.CLOSED:
            self.failed += 1
            if self.failed >= self.failures:
                self.state = State.OPEN

    def recover(self) -> None:
        if self.state is State.OPEN:
            self.state = State.HALF_OPEN


if __name__ == "__main__":
    breaker = CircuitBreaker()
    breaker.failure()
    breaker.failure()
    breaker.recover()
    print(breaker.state.value, breaker.allow())
