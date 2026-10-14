# E01 independent review

Verdict: **REOPEN**. The live PostgreSQL and replay experiments cover much of E01, but v1 does not satisfy the original roadmap's explicit requirement to record event keys, versions and source positions. This is a semantic implementation gap, not a test-count issue.

## Actual verification

Started the dedicated `infra/e01.compose.yaml` PostgreSQL 16 service and ran:

`E01_DATABASE_URL='postgresql://e01:e01_local_only@127.0.0.1:55450/e01' uv run python -m pytest tests/dataflows/cdc -q`

Result: **6 passed in 2.35s**. The tests extract `common.py` and each v0-v4 module from complete tutorial fences into fresh temporary packages, verify source equality and run real PostgreSQL `test_decoding`/slot experiments. The owned E01 container/network was then removed with `docker compose -f infra/e01.compose.yaml down -v`.

Observed source behavior includes v0 dual-write inconsistency; v1 real INSERT/UPDATE/DELETE text from `test_decoding`; v2 snapshot plus post-snapshot insert deduplication; v3 SQLite projection/checkpoint transaction replay; and v4 20,000-row paused-slot WAL retention, >20,000 decoded events and confirmed-flush advancement.

## Blocking finding

`labs/dataflows/cdc/v1.py:9-10` defines `changes()` as:

```python
return [(int(lsn, 16) if False else 0, text) for lsn, text in ...]
```

Every event is therefore returned with source position `0`; the actual PostgreSQL `lsn` is deliberately discarded. `experiment()` only returns event count and booleans for INSERT/UPDATE/DELETE. It does not return or assert ordered, distinct source positions, transaction/version metadata or stable event keys. The current tests pass because they check only text presence and count (`len(events) >= 5`). This fails roadmap v1's “记录事件键、版本和来源位置” requirement and leaves v2/v3 without a real source-position cursor to persist.

Repair should preserve each `lsn` in a structured event record, assert monotonic/distinct source positions for the decoded stream, expose transaction/event identity and operation/version fields appropriate to PostgreSQL 16 `test_decoding`, and carry the source cursor into the snapshot/increment handoff and v3 checkpoint. Do not replace this with a synthetic counter. The source position should be the connector value actually returned by PostgreSQL.

## Remaining evidence that is otherwise useful

v2 uses a slot created before the snapshot and deduplicates the overlapping source id; v3 atomically updates its deterministic SQLite projection and checkpoint on replay; v4 measures slot-retained WAL distance rather than claiming total filesystem usage and confirms the slot's flush position advances after consuming events. These parts do not cure the missing v1 source-position semantics.

Review artifact only; no implementation abstraction or source cleanup added.
