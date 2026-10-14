# D04 build evidence

Implemented Saga v0-v4 under labs/coordination/saga and tutorials/07-coordination/04-saga. v0 shows partial effects after delivery failure; v1 persists step states in SQLite and resumes after restart; v2 compensates in reverse with idempotent states; v3 retries timeout compensation and marks manual after bounded exhaustion; v4 uses concurrent order-scoped effect keys and makes Saga isolation limits explicit.

Validation: uv run python -m pytest tests/coordination/saga -q => 10 passed in 0.34s. Replay extracts the complete source fence for every version, checks exact source equality, and executes each version in a clean subprocess. Behavior tests cover partial failure, restart, duplicate compensation, manual intervention, and concurrent order isolation.

The SQLite file is the persistent state model; external services are represented by deterministic effect callbacks. This does not claim cross-database atomicity, rollback, serializable isolation, or durable external side effects. No commits or docs/progress changes.
