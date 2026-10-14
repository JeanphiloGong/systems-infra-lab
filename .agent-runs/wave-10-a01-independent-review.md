# A01 Independent Repair Review: REVISE

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## Commands and environment

The dedicated stack was started with:

```text
mkdir -p /tmp/a01-wal-archive
docker compose -f infra/e03.compose.yaml up -d --wait
```

The container became healthy on `127.0.0.1:55452` (`postgres:16.4`). The
replay command was:

```text
A01_DATABASE_URL='postgresql://a01:a01_local_only@127.0.0.1:55452/a01' \
  uv run pytest tests/recovery/backup -q
```

It produced `2 passed` for v0 and v1, then failed at v2 after 171.11s:

```text
RuntimeError: WAL interval not archived: ['0000000100000002']
1 failed, 2 passed in 171.11s (0:02:51)
```

The versions were then run independently:

```text
A01_DATABASE_URL='postgresql://a01:a01_local_only@127.0.0.1:55452/a01' \
  uv run pytest 'tests/recovery/backup/test_a01_replay.py::test_real_postgres_backup_restore[3]' -q
```

v3 failed after 92.80s:

```text
RuntimeError: WAL interval not archived: ['0000000100000007',
 '0000000100000008', '0000000100000009']
1 failed in 92.80s (0:01:32)
```

```text
A01_DATABASE_URL='postgresql://a01:a01_local_only@127.0.0.1:55452/a01' \
  uv run pytest 'tests/recovery/backup/test_a01_replay.py::test_real_postgres_backup_restore[4]' -q
```

v4 failed after 92.69s:

```text
RuntimeError: WAL interval not archived: ['000000010000000C']
1 failed in 92.69s (0:01:32)
```

At inspection time the healthy stack's archive directory contained only
`.backup` marker files and `recovery_hba.conf`; no ordinary WAL segment files
were present. The PostgreSQL logs showed checkpoints but no evidence that the
required segment files were available to the test's interval check.

## Fence parity

An independent extraction check passed for all v0-v4 tutorial files:

```text
v0-v4 exact common/source fence parity passed (10 checks)
```

The tutorial fences and implementation files are synchronized, but parity
does not establish that the physical backup and recovery path works.

## Decision

**REVISE.** The v0-v1 evidence from the full run is valid, and exact fence
parity passes. The required v2 physical base-backup/WAL interval experiment,
v3 successful target-time PITR, and v4 successful recovery plus deliberate
missing-segment failure were not independently demonstrated because all three
stop at WAL interval archival. Do not mark A01 accepted until the dedicated
stack archives the required segments and v2-v4 replay passes through the
recovery assertions.

No implementation, tutorial, plan, progress, or index files were changed;
only this review artifact was added. No abstraction or cleanup was introduced.
