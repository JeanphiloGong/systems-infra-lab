import pytest
from labs.traffic.retry.retry import PermanentError, RetryPolicy, RetryableError, call


def test_retryable_is_bounded_and_permanent_is_not_retried() -> None:
    attempts = 0
    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RetryableError()
        return "ok"
    assert call(flaky, RetryPolicy(max_attempts=3, deadline=1, base_delay=.1), lambda _: None) == ("ok", 3)
    assert attempts == 3
    attempts = 0
    with pytest.raises(PermanentError):
        call(lambda: (_ for _ in ()).throw(PermanentError()), RetryPolicy(), lambda _: None)
    assert attempts == 0


def test_deadline_and_policy_validation() -> None:
    with pytest.raises(TimeoutError):
        call(lambda: (_ for _ in ()).throw(RetryableError()), RetryPolicy(deadline=.01, base_delay=.1), lambda _: None)
    with pytest.raises(ValueError):
        call(lambda: "ok", RetryPolicy(max_attempts=0), lambda _: None)
