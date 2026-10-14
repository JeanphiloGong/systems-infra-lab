# E03 authored checkpoints awaiting independent review

Ownership: `labs/dataflows/events`, `tests/dataflows/events`, `tutorials/08-dataflows/03-events` and this evidence only. No commits, progress edits or changes to E01/E02.

Read original roadmap E03 v0-v4. Implemented a persistent SQLite event stream and versioned projection teaching chain:

- v0 exposes the current-state-only history gap.
- v1 appends immutable `(stream, version, kind, payload)` events and replays a finite order state machine, rejecting illegal transitions.
- v2 appends with `BEGIN IMMEDIATE` and expected stream version using two file-backed SQLite connections in real threads; stale concurrent writers raise `Conflict` without overwriting the first event.
- v3 records processed `(stream, version)` keys with projection updates, deduplicates redelivery, rejects skipped versions, and rebuilds a lagging read model from the event sequence.
- v4 upcasts old event payloads and keeps rebuild state-only; explicit new-event dispatch is the only side-effect path.

Verification:

`uv run pytest tests/dataflows/events -q` -> **5 passed in 0.40s**. Each case extracts the complete version fence into a new temporary directory, checks exact source equality, runs a fresh interpreter with isolated PYTHONPATH and validates semantic output. Direct v0-v4 scripts also ran successfully; v2 was repeated five times with one winner and one conflict each run.

Limits are explicit: one SQLite process, no cross-service transaction, no global event order, no CDC connector, no distributed projection coordinator, and external side-effect idempotency remains the caller's responsibility. The event log is the domain fact source; it is deliberately distinct from capturing changes in an existing database.
