# E01 independent review

Verdict: **pass** for v0-v4 after the handoff repair.

## Verification

The dedicated PostgreSQL 16 service was started with `infra/e01.compose.yaml`.
`E01_DATABASE_URL=postgresql://e01:e01_local_only@127.0.0.1:55450/e01 uv run
pytest tests/dataflows/cdc -q` returned **8 passed in 3.76s**. The tests extract
all tutorial source fences into fresh temporary packages, verify exact source
parity, and run each version against PostgreSQL logical decoding.

The accepted evidence includes real LSN/xid/event identity and numeric ordering;
an explicit `SHARE`-lock snapshot cut; mixed post-cut INSERT, UPDATE, DELETE and
delete/reinsert projection equality; decoding of spaces, apostrophes, backslashes,
newlines, empty strings and NULL; and rejection of unsupported layouts. v3
replays the same mixed stream through fresh subprocesses that exit before target
commit, after target commit before source acknowledgement, and during recovery.
SQLite projection/checkpoint state and PostgreSQL slot peek/ack behavior prove
rollback, idempotent replay and acknowledgement only after durable target commit.
v4 verifies paused-consumer WAL retention and confirmed flush progress.

An earlier independent probe found INSERT-only behavior; the author replaced it
with the lock-backed mixed-operation protocol. The old probe now passes its
UPDATE/DELETE boundary intent through the new exact projection checks.

The tutorial states connector ordering and process/host limitations. PostgreSQL
and the dedicated container were cleaned after verification. No blocking findings.
