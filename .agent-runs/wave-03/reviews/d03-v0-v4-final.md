# D03 independent review: v0-v4

Verdict: PASS against the original D03 scope in `docs/roadmap.md:467`, within the documented process-failure and state-model boundaries. No blocking findings.

## Actual verification

- Read `pg.py`, v0-v4 source, all five tutorial checkpoints, README configuration/cleanup instructions, and extraction tests.
- Ran `D03_DATABASE_URL='postgresql://d03:d03_local_only@127.0.0.1:55434/d03' uv run python -m pytest tests/coordination/commit -q`: **9 passed in 8.57s**.
- These tests extract complete printed dependencies into temporary directories, enforce source/fence equality, and execute the extracted scripts with temporary-directory PYTHONPATH. PostgreSQL experiments include v0, v1 and four v2 failure/decision modes; state models include v3 and v4.
- Queried the dedicated container with psql: PostgreSQL **16.14**, `max_prepared_transactions=20`, **zero remaining prepared transactions**.

## Scope and semantic checks

- v0 genuinely commits one local database transaction and rolls back the second after an injected application failure: balances `[70,100]`.
- v1 uses actual PostgreSQL PREPARE and COMMIT PREPARED; separate readers see `[100,100]` before resolution, with two prepared transactions, then `[70,130]`.
- v2 executes a child process ending with `os._exit(23)`. SQLite FULL-sync commits the decision before any commit delivery. Recovery reads that journal in the surviving parent. Sequential attempts to change an existing decision are rejected.
- Conflicting updates with a 50ms lock timeout observe real prepared locks after process death. Partial delivery leaves only the second resource prepared and locked; recovery skips the resolved GID and commits the remaining one. Repeated recovery preserves the result.
- Missing journal returns `in_doubt` without resolution. The supervisor's explicit abort is justified by this controlled execution stopping before any decision was sent, not by timeout or a participant guessing.
- Cleanup enumerates only newly generated databases owned by the experiment. It does not sweep unrelated databases or the shared lab server. Teardown rollback is clearly distinguished from transaction recovery.
- v3 has explicit legal READY/PRECOMMIT/COMMITTED transitions and rejects skipping precommit. Its 12 versus 8 message comparison includes final acknowledgments in both protocols.
- v4 is clearly labeled an unsafe local-timeout counterexample, not a complete 3PC implementation. A partition produces `[committed,aborted]` from `[precommit,ready]`.

## Limits retained

Two databases share one PostgreSQL server. Only coordinator process failure is exercised, not host/disk failure. The supervisor retains participant identities; journal replication, concurrent coordinators/recovery, arbitrary crash points during journal initialization, and full 3PC termination are not verified. Decision immutability evidence is for this single-coordinator sequential use, not a concurrent fencing protocol. Atomic outcome agreement does not promise an instantaneous cross-resource read snapshot.

Review artifact only; no implementation abstraction added and no source cleanup performed.
