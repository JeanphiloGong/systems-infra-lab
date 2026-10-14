# F03 v2/v4 repair re-review

Verdict: PASS for the reopened timing-accounting, actual-backoff and executed-layered-budget defects. Supersedes `f03-v2-v4-original-scope-reopened.md` for these defects. Hard preemption of arbitrary synchronous operations remains explicitly outside the implementation; this verdict must not be presented as a hard end-to-end runtime guarantee.

Actually ran `uv run python -m pytest tests/traffic/retry -q`: **18 passed in 0.89s**. This includes extracting repaired source and printed semantic checks into isolated temporary directories, verifying source/fence equality and running those checks in fresh subprocesses. Read both revised chapters and their printed checks, not only pytest status.

Also independently reran the original real-time reproductions:

- A 60ms first operation failure under deadline20ms now raises TimeoutError after **0.060292s**, with **one invocation**, rather than starting a second invocation and returning success after120ms.
- Three failures with base delay0.2 now take **0.600656s** with the real default sleeper, rather than64 microseconds with a no-op sleeper.

## Verified changes

- v2 uses a monotonic expiration instant, counts operation time/sleep overshoot, rejects attempts after expiry and rejects late success. Permanent errors remain terminal; attempt exhaustion preserves the final RetryableError.
- Printed fake-clock cases cover late success, slow failure, oversleep and zero deadline. Fake sleep advances the same clock. Real-sleep checks observe at least10ms and20ms separation between attempts.
- Eight independent simulated clients use distinct fixed seeds. No-jitter retries coincide, jitter retries spread, and repeated seeded runs reproduce the same arrivals within the specified bounds. This is a distribution model, not throughput measurement.
- v4 now actually invokes three nested retry layers. Instrumented leaves execute27 times without a shared quota and10 with Budget(10). The budget is consumed at the leaf, terminal exhaustion propagates through all layers, and reuse of the exhausted object starts no extra leaf work.
- Early success consumes only two tokens; permanent errors consume one attempt and stop; zero/expired deadlines and late success stop without multiplying retries. All layers share one expiration instant.
- Obsolete arithmetic-only helpers and their formula-only callers were replaced. No compatibility wrapper preserves the old misleading behavior.

## Remaining boundary

The original roadmap's bounded-total-time invariant requires operation-level timeout/cancellation as well as retry admission checks. These synchronous helpers cannot preempt a hung callable: the real reproduction necessarily returns at60ms despite a20ms deadline. The revised text states this clearly and does not claim hard cancellation or rollback of effects. Actual network/tool adapters must enforce their own remaining-time limits before any production end-to-end deadline claim. Budget is single-threaded and request-scoped, with leaf attempts as its unit; it is not a distributed quota.

Review artifact only; no implementation abstraction or source cleanup added by reviewer.
