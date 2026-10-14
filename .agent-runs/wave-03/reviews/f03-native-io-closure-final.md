# F03 native-I/O closure review

Verdict: PASS for the original F03 v2 deadline invariant with the documented boundary between retry policy and operation-level cancellation. The concrete socket checkpoint supplies the missing bounded-I/O evidence; arbitrary synchronous callable preemption remains explicitly out of scope.

## Verification

Actually ran:

- `uv run python -m pytest tests/traffic/retry -q`: **19 passed in 0.93s**.
- `uv run python labs/traffic/resilience/io_deadline.py`: `attempts=1`, `timed_out=true`, `thread_stopped=true`, elapsed **0.050607s** for a **0.05s** budget.

The focused test extracts both `v2.py` and `io_deadline.py` from the tutorial into an empty temporary directory, checks each extracted fence against the source, runs a fresh subprocess, parses observed timing/attempt/thread results, and requires elapsed <1s. The broader tests retain fake-clock operation-time/oversleep checks, real default sleep checks, seeded jitter distribution checks, and layered budget behavior.

## Semantics

`io_deadline.py` starts a real loopback server that accepts but never replies. One absolute monotonic expiration is shared by `connect`, `recv`, and the retry policy. Each native socket operation receives the remaining budget through `settimeout`; the resulting `TimeoutError` is terminal, so the stalled request has exactly one attempt. Event and thread cleanup are bounded and verified.

This demonstrates a concrete OS I/O boundary under ordinary scheduling, rather than claiming hard real-time behavior. The measured elapsed time may exceed the nominal deadline slightly due to scheduling. The guide correctly states that a generic Python callable can still run past the policy deadline, and that rejecting a late result does not undo external side effects. Production network/tool adapters must provide comparable native timeout/cancellation semantics before claiming an end-to-end bound.

No retry is performed after socket timeout, so the example does not demonstrate retrying a retryable socket failure with remaining budget; the shared absolute-expiration design and earlier fake-clock checks cover admission/overshoot. The checkpoint is sufficient to close the prior blocker about all timing evidence being synthetic or a no-op sleep.

Review artifact only; no implementation abstraction or source cleanup added.
