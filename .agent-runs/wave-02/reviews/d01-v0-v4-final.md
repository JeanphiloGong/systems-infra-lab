# D01 v0-v4 final rereview

Verdict: pass against the original roadmap scope.

The v1 checkpoint now claims the request key and order creation under one
explicit lock, standing in for an atomic unique constraint/transaction. Its
8-thread barrier experiment returns `order-1` to every caller and leaves one
business order. v0-v4 cover response-loss duplication, transaction
before/after-commit boundaries, fingerprint conflicts, processing/completed
states, retention expiry, and external receiver idempotency versus duplicate
risk.

Independent verification:

```text
uv run pytest tests/coordination/idempotency -q
12 passed in 0.28s
uv run pytest tests/coordination/idempotency/test_replay_d01.py -q
6 passed in 0.24s
```

Replay extracts each exact tutorial fence and executes it in subprocesses;
the concurrent v1 behavior is separately exercised by the focused test. No
reviewer source or tutorial edits were made.
