# F03: Retry Storm and Circuit Breaker

This tutorial is one evolving Python project under `labs/traffic/resilience/`. Each version is a complete, independently runnable checkpoint:

- v0 measures immediate retry amplification.
- v1 classifies retryable and permanent failures and adds a total deadline.
- v2 adds exponential backoff and seeded jitter.
- v3 bounds recovery probes with a circuit breaker.
- v4 executes nested retries and consumes a shared leaf-attempt budget.

The first pass intentionally uses no side effects. Idempotency and reconciliation belong to the later D01 dependency, where retrying a side effect can be made safe. Extract the exact checkpoint fence in each tutorial version and run the focused tests with `uv run python -m pytest tests/traffic/retry -q`.

