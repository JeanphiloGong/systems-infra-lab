# F03 build evidence

F03 now follows the roadmap target `labs/traffic/resilience/`:

- v0 `v0.py`: immediate retry and attempt amplification.
- v1 `v1.py`: retryable versus permanent failures and a total deadline.
- v2 `v2.py`: exponential backoff with injectable, seedable jitter.
- v3 `breaker.py`: closed/open/half-open transitions with one bounded probe.
- v4 `budget.py`: multiplicative layered retry bound and an end-to-end cap.

Each tutorial version contains one complete source fence marked with its exact target path. `tests/traffic/retry/test_replay_f03.py` extracts each fence into an isolated temporary file, executes it, and checks the version-specific behavior. The focused command `uv run python -m pytest tests/traffic/retry -q` passes: **15 passed in 0.49s**.

The v1 deadline uses an injectable monotonic clock, and replay covers deadline exhaustion as well as the version boundaries. The initial F03 pass intentionally has no external side effects. Idempotency and unknown-side-effect reconciliation remain in the later D01 dependency, as required by the roadmap. The focused suite now reports **16 passed in 0.55s**. No commits were made; independent review is still required.

