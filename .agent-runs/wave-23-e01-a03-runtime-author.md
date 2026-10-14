# E01/A03 runtime closure evidence

Ran the dedicated external-service experiments from clean stopped stacks.
Only the repository-owned Compose services were started.

E01 CDC:

```text
$ docker compose -f infra/e01.compose.yaml up -d --wait
systems-e01-postgres-1 Healthy
$ E01_DATABASE_URL='postgresql://e01:e01_local_only@127.0.0.1:55450/e01' uv run pytest tests/dataflows/cdc -q
8 passed in 3.76s
```

This covered all v0-v4 logical-decoding replays plus decoder value handling
and the snapshot-cut writer lock test against PostgreSQL 16 with logical
slots. The stack was removed with `docker compose -f infra/e01.compose.yaml
down -v`.

A03 Patroni/HA:

```text
$ ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd bash infra/a03-patroni/lab.sh up
$ uv run python -m labs.recovery.ha.patroni_probe
{"acknowledged_lost": 0, "new": "p2", "old": "p1", "old_process_alive": true,
 "old_write_rejected": true, "rejoin": "basebackup via Patroni reinitialize", ...}
$ uv run python tests/recovery/ha/replay_patroni.py --version 2 --live
live_executed=true, acknowledged_lost=0, old_write_rejected=true
$ uv run python tests/recovery/ha/replay_patroni.py --version 3 --live
live_executed=true, acknowledged_lost=0, old_write_rejected=true
$ uv run python tests/recovery/ha/replay_patroni.py --version 4 --live
live_executed=true, acknowledged_lost=0, old_write_rejected=true
$ A03_PATRONI_LIVE=1 uv run pytest tests/recovery/ha/test_patroni_probe.py tests/recovery/ha/test_a03.py -q
6 passed in 33.49s
```

The probe observed a promoted `p2`, retained acknowledged data, fencing of
the still-running old `p1`, reinitialization/rejoin, and planned cutback.
Cleanup used `ETCD_BINARY=... bash infra/a03-patroni/lab.sh down`; its two
Patroni containers, etcd container, volumes, and network were removed. A
post-cleanup Docker listing showed no matching stack containers. No unrelated
user service was stopped.

These are local disposable PostgreSQL/Patroni runs, not independent-host HA
or a production RTO/RPO guarantee. The observed RTO/client attempts vary by
run; acknowledged loss was zero because the probe waits for replication before
failure injection. No implementation changes, abstraction, docs/progress, or
index edits were made.
