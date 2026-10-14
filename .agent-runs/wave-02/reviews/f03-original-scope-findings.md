# F03 original-scope review

Verdict: not accepted.

The roadmap requires Retry Storm/Circuit Breaker progression: v0 immediate
retry amplification, v1 retryable versus permanent failures with a total
deadline, v2 exponential backoff and jitter, v3 closed/open/half-open circuit
state with bounded probes and recovery, and v4 layered retry-budget limits.

Current v3 is an operation-id cache (`OperationStore`) and current v4 is an
in-memory unknown-side-effect reconciler. Neither implements a circuit
breaker, probe budget, recovery transition, layered calls, or multiplicative
retry-budget limit. They are useful idempotency/reconciliation topics but are
outside the F03 roadmap checkpoint contract.

There is also a tutorial continuity defect in v0-v2: each document places a
full `retry.py` checkpoint before the version-specific `v0.py`, `v1.py`, or
`v2.py` fence. The generic replay regex executes that first full checkpoint,
while boundary tests separately inspect the later version file for feature
absence/presence. A reader following the printed first checkpoint therefore
starts with final retry policy behavior rather than the intended incremental
version.

No reviewer source, tutorial, or progress-file edits were made.
