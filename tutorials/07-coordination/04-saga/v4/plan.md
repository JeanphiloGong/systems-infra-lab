# D04 v4: concurrent orders and idempotent effects

Scenario: two orders execute concurrently, and the same reserve request for `order-a` is delivered twice.

Pressure/change: key effects by order and operation, then reject duplicate application while allowing `order-b` independently.

Checkpoint: `orders.apply('order-a','reserve')` is true once and false on duplicate; `order-b` is true; snapshot shows isolated order state.

Limit: local in-memory idempotency and no distributed transaction coordinator. Later coordination topics address durable deduplication and cross-service consistency.

Replay: `uv run pytest tests/coordination/saga/test_replay_d04.py -q`.
