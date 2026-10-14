# F01 build evidence

Implemented actual `psycopg_pool.ConnectionPool` integration via `make_pool`; removed custom queue pool to avoid transaction/session reset and checked-out close bugs. URL uses `SYSTEMS_LAB_DATABASE_URL`.

`uv add psycopg-pool>=3.2,<4` completed. Local PostgreSQL accepts connections on the isolated compose port, but this shell did not export the URL, so two integration tests skip (`2 skipped`) rather than claim a live run. Tests require the URL to verify reuse and exception cleanup against real PostgreSQL.

Completed tutorials and strict replay:

- `tutorials/01-storage-engines/07-connections/v0/tutorial.md`: direct connection baseline.
- `v1`: official `psycopg_pool.ConnectionPool`, reuse and bounded checkout.
- `v2`: held-checkout exhaustion, timeout, and exception-safe return.
- `v3`: session/transaction ownership and the pooling-versus-multiplexing boundary.
- `tests/traffic/connections/replay_f01.py` extracts each checkpoint into a temporary directory and executes it against the configured PostgreSQL DSN; it does not import the worktree implementation.

Live verification on 2026-10-13:

```text
SYSTEMS_LAB_DATABASE_URL=postgresql://...@127.0.0.1:55432/systems_lab uv run pytest tests/traffic/connections/test_f01_pool.py -q
.....                                                                    [100%]
5 passed in 0.48s

SYSTEMS_LAB_DATABASE_URL=postgresql://...@127.0.0.1:55432/systems_lab uv run python tests/traffic/connections/replay_f01.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

The replay output also included the checkpoint observations: v0 returned `1`, v2 observed bounded exhaustion and recovery, and v3 asserted `application_name_after_return='f01-v3'` plus transaction status `IDLE`. That persisted setting is intentional evidence that application-specific session state needs an explicit policy.

The measured results are local integration evidence. They do not claim production throughput, physical disk behavior, or universal server-side session reset semantics.
