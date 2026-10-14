# T03 build evidence

v0 implemented and tested against PostgreSQL16.14: `uv run python -m pytest tests/transactions/locking/test_t03_locking.py -q` -> 1 passed. Two autocommit connections read 10 then write 9; final quantity 9.
v1 implemented: version-conditional update returns `(1, 0)` and final `(9, 1)`; same command now reports 2 passed in 0.32s. v0 schema is one row without version; v1 tutorial explicitly replaces it with version schema.

v2 row-lock experiment uses Event + pg_blocking_pids (no sleeps): real PostgreSQL test passes and reports final quantity 8 with measured wait/hold intervals. v3 Barrier(2) opposite-order locks deterministically produces one DeadlockDetected victim; its full transaction retry gives `(1,8,8)` and fixed order gives `(8,8)`. v4 is an explicitly PostgreSQL-independent LockModel; two tests cover escalation failure, metadata reduction and broadened blocking. Current locking suite: **6 passed in 1.45s**.

v0-v4 tutorials now include complete source checkpoints, setup, commands, and typed module entrypoints. Independent review pending; no acceptance claimed.
