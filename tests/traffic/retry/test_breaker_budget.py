import pytest
from labs.traffic.resilience.breaker import CircuitBreaker, State
from labs.traffic.resilience.budget import amplification, call_layers


def test_closed_open_half_open_probe_recovery() -> None:
    breaker = CircuitBreaker(2); assert breaker.allow(); breaker.failure(); breaker.failure(); assert breaker.state is State.OPEN; assert not breaker.allow(); breaker.recover(); assert breaker.state is State.HALF_OPEN; assert breaker.allow(); assert not breaker.allow(); breaker.success(); assert breaker.state is State.CLOSED


def test_layered_attempts_multiply_and_validate() -> None:
    assert amplification(None) == 27
    assert amplification(10) == 10
    with pytest.raises(ValueError): call_layers(lambda: None, layers=-1)
