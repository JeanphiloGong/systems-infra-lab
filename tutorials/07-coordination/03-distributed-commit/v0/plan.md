# D03 v0: local commit cannot span databases

Scenario: debit and credit live in separate PostgreSQL databases. A local commit on the debit database can succeed before the credit operation fails.

Pressure/change: freeze `pg.py` and `v0.py`; execute the debit, force credit failure, and verify balances `[70, 100]`.

Limit/next: no prepare or recovery decision exists, so the two resources diverge. v1 prepares both resources before deciding.

Replay: `uv run pytest tests/coordination/commit -q` or `uv run python labs/coordination/commit/v0.py` (requires disposable PostgreSQL).
