# D04 v0: serial Saga leaves partial effects

Scenario: reserve inventory, charge payment, then fail shipment. The forward steps have already changed independent services.

Pressure/change: freeze `v0.py` with serial steps and no compensation; force shipment failure and print inventory, charged, and shipments.

Checkpoint: failure leaves inventory reserved and payment charged while shipment is absent; replay asserts the partial state.

Limit/next: no durable progress or rollback. v1 persists step progress and resumes after restart.

Replay: `uv run pytest tests/coordination/saga/test_replay_d04.py -q`.
