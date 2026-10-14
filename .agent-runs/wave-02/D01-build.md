# D01 build evidence

D01 uses deterministic in-memory coordination models under `labs/coordination/idempotency/`:

- v0 `v0.py`: response loss followed by a retry creates duplicate orders.
- v1 `v1.py`: request keys replay the original response, with an explicit lock representing the atomic uniqueness boundary for concurrent duplicates.
- v2 `v2.py`: business record and deduplication record share modeled transaction boundaries; before-commit and after-commit crashes differ.
- v3 `v3.py`: canonical payload fingerprints reject key reuse with different parameters; processing state, completed response replay, and retention expiry are visible.
- v4 `v4.py`: local order deduplication does not control an external mail side effect unless the receiver supports the same idempotency key.

Each tutorial version under `tutorials/07-coordination/01-idempotency/` contains one complete source fence marked with its exact target path. Replay extracts and executes all five fences in isolated subprocesses.

Verification:

```text
uv run python -m compileall -q labs/coordination/idempotency
uv run python -m pytest tests/coordination/idempotency -q
12 passed
```

Exactly-once is deliberately scoped to the durable key, payload, effect store, receiver contract, and retention window. The model does not claim network-level exactly-once delivery. No commits were made; independent review is required.

