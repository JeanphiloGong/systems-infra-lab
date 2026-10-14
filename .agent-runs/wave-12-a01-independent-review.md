# A01 Independent Repair Review: PASS

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## Independent replay

The dedicated PostgreSQL 16.4 stack was started with:

```text
docker compose -f infra/e03.compose.yaml up -d --wait
```

Against `postgresql://a01:a01_local_only@127.0.0.1:55452/a01`, the complete
replay passed:

```text
$ A01_DATABASE_URL='postgresql://a01:a01_local_only@127.0.0.1:55452/a01' \
    uv run pytest tests/recovery/backup -q
.......                                                                  [100%]
7 passed in 24.25s
```

This includes the five extracted v0-v4 experiments, the WAL segment-name
regression, and the exact fence test.

## Physical backup and recovery observations

Direct v2 output:

```json
{"corruption_detected": true, "partial_restore_accepted": false,
 "physical_backup": true, "base_backup_complete": true,
 "wal_start_lsn": "0/A02C8D8", "wal_end_lsn": "0/A02CA30",
 "required_wal_segments": ["00000001000000000000000A"],
 "archive_continuous": true}
```

Direct v3 output:

```json
{"physical_backup": true, "base_backup_complete": true,
 "target_rows": "1:100,2:100", "later_rows_absent": true,
 "deleted_row_restored": true, "current_rows": "1:100,3:300",
 "wal_start_lsn": "0/C02ACD8", "wal_end_lsn": "0/E0002A8",
 "required_wal_segments": ["00000001000000000000000C",
 "00000001000000000000000D", "00000001000000000000000E"],
 "archive_continuous": true}
```

Direct v4 output:

```json
{"missing_archive_detected": true, "recovery_failed": true,
 "successful_recovery": true, "recovery_elapsed_seconds": 3.464165581855923,
 "failed_attempt_elapsed_seconds": 7.2581654959358275,
 "acknowledged_rows_before_target": 2, "recovered_rows": "1:100,2:100",
 "post_target_rows_not_recovered": 1,
 "data_loss_window": "id=3 committed after target and absent from target recovery",
 "required_wal_segments": ["000000010000000000000011"],
 "archive_continuous": true}
```

The archive directory contained ordinary 16 MiB WAL files for the required
intervals, including segments `...00000A`, `...00000C` through `...00000E`,
and `...000011`; marker files were also present. The v4 output proves both a
successful target-time recovery and a separate failed attempt after a segment
was removed from the private archive copy.

## Tutorial parity

An independent extraction check compared `common.py` and each v0-v4 source
fence with the repository files:

```text
v0-v4 exact tutorial/source fence parity passed: 10 checks
```

## Decision

**PASS.** A01 now demonstrates independent restore and constraints (v0),
post-backup exclusion (v1), physical base backup plus complete WAL interval
and corruption branch (v2), successful target-time PITR (v3), and measured
successful/failed recovery with an explicit loss window (v4).

The dedicated stack was stopped and removed with
`docker compose -f infra/e03.compose.yaml down -v` after verification. No
implementation, tutorial, plan, progress, or index files were changed; only
this review artifact was added. No abstraction or cleanup was introduced.
