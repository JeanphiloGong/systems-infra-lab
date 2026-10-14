# E02 independent review

Verdict: **pass** for v0-v3.

## Verification

The dedicated PostgreSQL 16 service was started and
`E02_DATABASE_URL=postgresql://e02:e02_local_only@127.0.0.1:55451/e02 uv run
pytest tests/dataflows/schema_evolution -q` returned **5 passed in 2.86s**.
Every version extracts its complete `common.py` and version source fences into
a fresh package, checks exact parity and runs against the isolated database.

v0 reproduces the old-client failure after a direct rename. v1 verifies an
additive nullable column, `COALESCE` reads and transition dual writes. v2 now
uses fresh workers: one commits and exits, one exits before commit and rolls its
batch back, a new worker resumes from the persisted PostgreSQL checkpoint, and
a repeated fresh worker performs zero work. The NULL guard preserves a value
written by the new client. v3 proves the populated column can become `NOT NULL`,
the legacy column can be removed, and the old query is rejected.

The tutorial states that dual-write compatibility is transitional and that the
final checkpoint removes it. No blocking findings; E02 v0-v3 are accepted.
