# A01 PITR repair review: replay failure

The archive-enabled stack started successfully, but the independent command

```text
A01_DATABASE_URL=postgresql://a01:a01_local_only@127.0.0.1:55452/a01 \
uv run pytest tests/recovery/backup -q
```

returned **1 failed, 5 passed**. The extracted v3 tutorial failed its required
assertion `ready and rows == "1:100,2:100"`; the recovery instance did not return
the target-time state. A direct retry also exposed a non-idempotent seed when
the source state already contained id=3, and the failed Docker-mounted
`pg_basebackup` left root-owned files that caused `TemporaryDirectory` cleanup
permission errors. The dedicated containers and archive were cleaned afterward.

The PITR implementation is therefore not yet independently accepted. Repair
must make each extracted version deterministic on a clean dedicated database,
choose a target timestamp guaranteed after the base backup and before the later
delete/insert, wait for archive completion/recovery completion rather than
equating `pg_isready` with recovery target reached, and clean mounted files
without leaving permission artifacts. Re-run all v0-v4 fences and missing/
corrupt archive checks before requesting review again.

Second independent replay: **1 failed, 5 passed in 48.31s**. v3 still failed.
Actual recovery logs reported missing WAL and `recovery ended before configured
recovery target was reached`. `pg_stat_archiver` showed failed_count=48 and
last_failed_wal=000000010000000000000003.00000028.backup. The archive command
`test ! -f /archive/%f && cp %p /archive/%f` rejected an existing identical
backup-history file, repeatedly blocking later WAL. Required repair: isolated
per-cluster archives, retry-safe existing-file comparison, and explicit archive
completion checks. A fixed sleep is not evidence of complete WAL archival.
