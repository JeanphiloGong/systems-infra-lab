# D03 build evidence

Status: implemented, awaiting independent review. No commits and no docs/progress.md changes.

## Roadmap coverage

- v0 uses two independently created PostgreSQL databases. First transaction commits debit; the second fails and rolls back. Observed balances [70,100], total 170.
- v1 uses actual PostgreSQL PREPARE TRANSACTION / COMMIT PREPARED. Preflight checks max_prepared_transactions >= 2. Two prepared records retain old reader-visible [100,100]; commit produces [70,130].
- v2 spawns a real worker that calls os._exit(23) after preparing both, optionally recording a durable decision and optionally delivering only the first commit. SQLite synchronous=FULL records one immutable decision. Tests observe prepared counts and real row lock_timeout failures. Recovery covers commit, abort, missing decision (in_doubt without mutation), repeated delivery and partially committed [70,100] becoming [70,130]. Missing-decision test aborts only after the supervisor knows the terminated worker never sent a decision.
- v3 is a labeled state-machine experiment with legal READY/PRECOMMIT/COMMITTED transitions and command+reply counts 12 vs 8 under the stated failure-free counting convention.
- v4 delivers precommit to only one participant, loses the coordinator and partitions the participants. An intentionally unsafe local timeout shortcut produces COMMITTED/ABORTED, demonstrating why removing synchronous/failure assumptions invalidates that shortcut. It is explicitly not a complete 3PC implementation.

## Execution evidence

Dedicated disposable PostgreSQL 16.14 container systems-d03-postgres at localhost:55434, max_prepared_transactions=20. Role/database d03, local tutorial password d03_local_only. Container remains running for independent review. Shared PostgreSQL and infra files were not changed. Creation and teardown commands are in the D03 README.

```bash
D03_DATABASE_URL='postgresql://d03:d03_local_only@127.0.0.1:55434/d03' uv run python -m pytest tests/coordination/commit -q
```

Result: **9 passed in 8.69s**. All versions extract complete Markdown fences, including each source dependency, into a fresh temporary directory. Subprocess import paths point there; repository Python code is not used to supply omitted dependencies. Tests compare every fence to its source file and assert semantic outputs, not merely zero exit status. Additional assertions reject decision changes and phase skipping and check no D03 prepared transactions remain.

## Boundaries and cleanup

Two databases share one server; this is real database transaction and coordinator-process failure, not independent database-host crash. The local decision journal is not replicated, participant identities remain with the supervisor, and durable storage assumptions do not cover host loss. Teardown resolves only prepared transactions in this experiment's uniquely owned temporary databases, then drops those databases. Teardown is not the recovery algorithm.

The setup/cleanup helper pg.py is a permanent local tutorial helper needed for three PostgreSQL checkpoints. No compatibility layer or temporary abstraction was added. Cleanup removes temporary databases, journals and replay directories; the dedicated reviewer server remains running. No consensus, full production 3PC termination or global snapshot isolation is claimed.
