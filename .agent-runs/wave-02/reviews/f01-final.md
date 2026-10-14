# F01 independent review

Verdict: pass, with one documentation clarification requested for v3.

The implementation now uses the official `psycopg_pool.ConnectionPool` and
the repository's `SYSTEMS_LAB_DATABASE_URL`. v0 measures one connection per
operation; v1 verifies bounded reuse; v2 demonstrates timeout while a slot is
held and recovery after an exception; v3 establishes the transaction boundary
and explains that pooling does not multiplex concurrent protocols.

The replay extracts each version's single checkpoint into a fresh temporary
directory and executes every non-pytest command in the printed check blocks.
The live replay produced:

```text
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

The v3 output on the installed psycopg-pool version was:

```text
{'reused_session': True, 'application_name_after_return': 'f01-v3'}
{'transaction_status': 'IDLE'}
```

This confirms that `application_name` persists across reuse in this setup.
The guide already says the exact reset policy is library/database-specific and
that request-specific state should be set inside checkout; make that observed
persistence explicit so readers do not infer that every session setting is
cleared by pool reset.

Independent verification:

```text
uv run pytest tests/traffic/connections -q
5 passed in 0.36s
```

Tests cover direct query, identity reuse, exception recovery, bounded timeout,
and post-failure checkout. No reviewer source edits were made.
