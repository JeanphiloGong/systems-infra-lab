# F01 plan: connection pooling

One real scenario drives all four versions: a request handler runs a short PostgreSQL query.

| Version | Pressure | Change | Verification |
| --- | --- | --- | --- |
| v0 | Every request opens a session | Direct `psycopg.connect` baseline | Query succeeds; elapsed time is reported |
| v1 | Startup cost and unbounded session creation | Official `ConnectionPool` with `max_size` and `timeout` | Sequential borrows reuse a session |
| v2 | A leaked checkout blocks all borrowers | Context-managed checkout and bounded timeout | `PoolTimeout` plus post-exception recovery |
| v3 | Session/transaction state crosses request boundaries | Explicit checkout ownership and transaction completion | Reset observation and completed transaction status |

The examples use `SYSTEMS_LAB_DATABASE_URL`, an isolated local PostgreSQL service, and `psycopg-pool>=3.2,<4`. Pooling limits physical sessions; it does not multiplex concurrent PostgreSQL protocols over one session. Replay extracts each fenced checkpoint into a temporary directory and runs its command against the configured DSN.
