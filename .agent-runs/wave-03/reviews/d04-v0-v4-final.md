# D04 independent Saga review

Verdict: PASS against `docs/roadmap.md:482` within the tutorial's deterministic external-effect model. No blocking findings.

## Actual verification

Ran `uv run python -m pytest tests/coordination/saga -q`: **10 passed in 0.30s**. The replay test extracts each v0-v4 source fence to a fresh subprocess and checks source/fence equality; behavior tests independently exercise partial effects, SQLite restart, reverse compensation, bounded manual state and concurrent order isolation. Read all version tutorials, README and roadmap rather than relying on the build summary.

## Scope evidence

- v0's three service calls leave inventory and charge effects after delivery raises; no false rollback is reported.
- v1 commits step progress in SQLite before the effect and after success. Reopening the same database skips a completed step, demonstrating restart continuation without blindly repeating that completed state.
- v2 compensates in reverse position order and persists `compensated`; duplicate compensation is a no-op. The prose correctly calls these business operations, not database rollback.
- v3 retries timeout compensation up to a caller-selected bound, persists attempt count, and transitions to `manual` after exhaustion. `manual`, permanent errors and retry semantics are visible state rather than hidden success.
- v4 uses `(order_id, effect name)` primary keys and a lock around the SQLite transaction. Concurrent duplicate attempts for two orders produce exactly one effect per order and retain separate snapshots. The tutorial explicitly states that a Saga does not provide database-level isolation for shared inventory/capacity or intermediate reads.

## Boundaries and residual semantics

The source uses deterministic callbacks for external services, not actual independent databases or durable network effects. If a real effect succeeds and the process dies before its SQLite `done`/`compensated` marker, retry can execute it again; idempotency must therefore be enforced by the external service/effect key. Similarly, a timeout callback may have an unknown side effect. The tutorials' effect-key and state model teaches this boundary but does not prove cross-service deduplication. There is no distributed transaction, serializable isolation, crash recovery protocol for external services, or global inventory reservation guarantee.

The v4 in-process SQLite lock serializes effect claims across orders; it proves key isolation and duplicate suppression, not parallel throughput or database row-level isolation. These limits are consistent with the original v4 requirement to explain Saga isolation rather than claim it is solved.

Review artifact only; no implementation abstraction or source cleanup added.
