# A01 backup/PITR boundary evidence

A01 uses a dedicated PostgreSQL 16 service at `127.0.0.1:55452` with WAL sender support. The five checkpoints use real PostgreSQL tools:

- v0 exports plain SQL with `pg_dump`, drops the source table, and restores it with `psql`.
- v1 exports custom format, adds a post-backup row, and restores only the two rows present at the dump point with `pg_restore`.
- v2 truncates a custom dump and verifies `pg_restore` fails rather than accepting a partial artifact.
- v3 runs `pg_basebackup --wal-method=stream`, starts a separate PostgreSQL recovery container with `recovery.signal` and `restore_command`, and restores to a timestamp before a delete/insert. The deleted row is present at the target and later row is absent.
- v4 removes the archived WAL needed by the same target recovery and verifies the isolated recovery instance fails instead of returning a partial database.

Validation:

```bash
docker compose -f infra/e03.compose.yaml up -d --wait
A01_DATABASE_URL='postgresql://a01:a01_local_only@127.0.0.1:55452/a01' uv run python -m pytest tests/recovery/backup -q
docker compose -f infra/e03.compose.yaml down -v
```

Result: **6 passed in 18.66s** after archive retry repair. Every chapter extracts complete common and version fences into an isolated temporary package, verifies exact source equality, and runs against dedicated PostgreSQL. v3/v4 also launch separate recovery containers and clean their data directories. No progress file or commit was changed.

The archive command namespaces files by PostgreSQL system identifier, treats an identical retry as success, and rejects a conflicting file. The lab uses a disposable archive directory and one controlled target timestamp. Production still needs durable archive retention, monitoring, timelines and a separately managed recovery service; this checkpoint proves the actual restore path and missing-archive failure rather than treating a dump as PITR.
