# D01 v0-v4 independent review

Verdict: not accepted yet against the original roadmap scope.

The complete fences replay and focused tests pass (`11 passed`), and v0-v4
cover response-loss duplication, request-key replay, transaction crash
boundaries, payload fingerprints, processing/completed/retention states, and
external receiver idempotency limits.

The v1 roadmap checkpoint explicitly requires validating both serial and
concurrent duplicate requests. The implementation and tutorial only assume
serialized access to `responses`; they have no lock/unique-constraint race
model and no concurrent duplicate test. Two simultaneous callers can both
observe an absent key and create two orders. Add a controlled concurrent
duplicate experiment or explicitly implement the unique atomic boundary before
acceptance. No reviewer source or tutorial edits were made.
