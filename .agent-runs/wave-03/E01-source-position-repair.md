# E01 source-position repair evidence

Scope: `labs/dataflows/cdc/common.py`, v1-v3, all five complete tutorial fences, and `tests/dataflows/cdc/test_e01_replay.py`. No progress file or commit changes.

Replaced synthetic source positions with structured events carrying actual PostgreSQL LSN, xid, operation, raw decoding text, event identity (`xid:lsn:operation`) and explicitly batch-local version. Transaction boundaries can share LSN with data rows; the test checks nondecreasing stream positions and distinct data-change positions rather than incorrectly requiring every boundary to have a unique LSN.

v2 records the slot creation LSN and final consumed source position. Corrected the SQL API misunderstanding: `pg_logical_slot_get_changes` receives NULL for `upto_lsn`; its second argument is not a start/resume position. LSN comparisons use PostgreSQL `pg_lsn` or numerical high/low hex parsing.

v2 now uses an explicit snapshot cut: a real PostgreSQL SHARE lock blocks writers while the complete source snapshot is read and the prior slot overlap is consumed. After release, a mixed transaction updates id 1 with a value containing spaces and an apostrophe, deletes ids 3 and 4, reinserts id 4, and inserts id 2. A strict `order_change` decoder preserves spaces, doubled quotes, backslashes, newlines, empty strings and NULL, and rejects unsupported test_decoding layouts. The projection must exactly equal the source table; a two-connection test proves writes are blocked only during the cut and appear afterward.

v3 records the real source position, event key and batch version in the same disk-backed SQLite transaction as the projection. The same mixed update/delete/reinsert stream runs through three fresh worker processes: terminate before target commit, terminate after commit but before source acknowledgement, then recover by rereading the actual PostgreSQL slot. `peek_changes` preserves source records until commit; bounded `get_changes` acknowledges only through the committed batch LSN. Parent assertions reopen SQLite and verify rollback, committed metadata, stable source identity across restart, idempotent replay, mixed projection equality and acknowledgement advancement. Workers receive no retained event list.

Verification on the dedicated PostgreSQL 16 service at port 55450:

```bash
E01_DATABASE_URL='postgresql://e01:e01_local_only@127.0.0.1:55450/e01' uv run python -m pytest tests/dataflows/cdc -q
```

Result: **8 passed in 3.94s**. All five versions were extracted from complete Markdown fences into fresh temporary packages, checked for exact source equality, and executed against real PostgreSQL. Assertions cover real LSN syntax/order, distinct data positions, xid/event identity, ordered INSERT/UPDATE/DELETE, version sequence, a lock-backed snapshot cursor, exact mixed projection equality, decoder edge cases, persistent checkpoint metadata, process exits at both commit boundaries and source acknowledgement after durable target commit.

Permanent learning abstractions added: the `Event` record, `read_events` decoding helper shared by v1-v3 and v3 worker subprocess entry point. Removed the old synthetic-position helper, stale tutorial copies and in-memory replay implementation; no compatibility layer. This is author evidence, not an independent reviewer verdict.
