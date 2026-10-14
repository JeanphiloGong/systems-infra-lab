# Wave 13 Q02/Q04 plan quality evidence

Date: 2026-10-14. Scope: only the nine version plans under `tutorials/04-query/02-indexes` (v0-v3) and `tutorials/04-query/04-derived` (v0-v4). No code, tutorial body, docs/progress, index, or other module was changed.

The nine generic plans were replaced with version-specific Pressure/Naive/Break/Change/Check/Freeze/Still-lacks/Next content derived from the current tutorial assertions and commands.

Q02 now records:

- v0: 100000-row baseline Seq Scan and result invariant.
- v1: selective predicate index choice versus common predicate Seq Scan.
- v2: composite index column order and buffer-access comparison.
- v3: visibility-map effects, updated-row heap fetches, VACUUM recovery, and Index Only Scan.

Q04 now records:

- v0: repeated aggregate baseline and 30 daily totals.
- v1: materialized-view staleness before/after refresh.
- v2: CONCURRENTLY prerequisites, SQLSTATE failures, and reader behavior.
- v3: deterministic cache-aside TTL loads/hits and stale-read boundary.
- v4: generation/expiry fence rejecting an in-flight stale cache fill.

Verification:

- `uv run python` plan field audit: 9/9 plans passed all eight fields and contained no old generic baseline phrase.
- `uv run pytest tests/query/indexes/test_q02_indexes.py tests/query/derived/replay_q04.py -q`: 2 passed.
- `uv run pytest tests/query/indexes/test_postgres.py tests/query/derived/test_postgres.py -q`: 2 passed, 9 skipped because the isolated PostgreSQL DSN/services were not running in this author environment. No live PostgreSQL result is claimed.

No new abstraction was added. The changes are permanent plan-document replacements; no temporary helper files were retained.
