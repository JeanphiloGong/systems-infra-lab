# F03 v2/v4 reopened-scope repair

Status: repaired, awaiting independent re-review. Supersedes the formula-only and synthetic elapsed-time evidence in wave-02/F03-build.md for these checkpoints. R03 files were left unchanged during this repair.

v2 now records one monotonic expiration time; checks before every attempt, after retryable failure, before sleep, and after successful work; defaults to time.sleep. Exhausted attempts preserve RetryableError, while elapsed deadline and late success raise TimeoutError. PermanentError is terminal. Synchronous work cannot be preempted; the guide explicitly requires actual I/O timeout/cancellation and warns that rejecting a late result does not undo effects.

Printed regression checks execute a 60ms simulated operation under a 20ms deadline (one invocation only), reject late success, reject a new attempt after sleep overshoot, and test a zero deadline. A real time.sleep default test observes three invocations separated by at least 10ms then 20ms. Eight simulated clients use distinct fixed seeds; no-jitter retries coincide, jitter retries spread and are reproducible with bounded arrival ranges. Fake sleep advances the same injected clock; no no-op sleeper remains as default.

v4 removed power/min calculators. Three actual nested retry loops invoke an instrumented failing leaf 27 times without a shared budget and 10 with Budget(10). Leaf entry consumes the shared budget; BudgetExhausted, PermanentError and TimeoutError are not retryable. Exhaustion persists on reuse; early success uses only two of ten tokens. All layers share one deadline, check operation time and reject late success. This is a single-threaded request-scoped leaf-attempt quota, not a distributed atomic quota system.

Verification: `uv run python -m pytest tests/traffic/retry -q` => **18 passed in 0.82s**. The added parametrized tests extract each version's full source and its printed regression-check fence to an empty directory, execute a fresh subprocess with isolated paths, and verify source/fence equality. Existing formula assertions were replaced with real amplification calls. Tutorials were rewritten in Chinese with timing/side-effect/simulation scope explained.

Permanent minimal Budget and BudgetExhausted types express shared consumable state and terminal exhaustion. No compatibility adapters added; obsolete arithmetic helpers removed and callers updated. No commits, shared progress edits or servers started for this repair.
