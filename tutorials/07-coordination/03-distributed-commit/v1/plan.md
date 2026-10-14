# D03 v1: prepare before deciding

Scenario: two databases prepare a transfer. Prepared state is not yet visible, but both resources must be ready before commit.

Pressure/change: add PREPARE TRANSACTION and a coordinator decision; freeze `v1.py`.

Checkpoint: before decision balances are `[100, 100]` and `prepared == 2`; after commit balances are `[70, 130]`.

Limit/next: a coordinator crash can leave prepared obligations. v2 journals the decision and recovers unknown outcomes.

Replay: `uv run pytest tests/coordination/commit -q` (requires PostgreSQL prepared transactions).
