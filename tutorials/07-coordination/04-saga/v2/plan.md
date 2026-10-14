# D04 v2: compensation is an ordered business operation

Scenario: shipment fails after inventory and payment succeeded; compensation must run in reverse forward order: refund payment (position 2), then release inventory (position 1).

Pressure/change: freeze `v2.py` with idempotent compensation markers; the caller supplies positions 2 then 1 rather than the journal automatically scheduling reverse order.

Checkpoint: printed effects are `reserved, charged, refunded, released`; repeating position 1 adds no duplicate effect, and status records both positions as compensated.

Limit/next: compensation can itself fail. v3 retries it and exposes manual intervention.

Replay: `uv run pytest tests/coordination/saga/test_replay_d04.py -q`.
