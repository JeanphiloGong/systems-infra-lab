# Wave-23 independent runtime review: E01/A03

## E01 CDC

Started the repository's dedicated stack with
`docker compose -f infra/e01.compose.yaml up -d --wait`, then independently
ran:

```text
E01_DATABASE_URL='postgresql://e01:e01_local_only@127.0.0.1:55450/e01' \
  uv run pytest tests/dataflows/cdc -q
........                                                                 [100%]
8 passed in 3.82s
```

This suite includes all v0-v4 logical-decoding fence replays, decoder values,
and the snapshot-cut writer-lock check. The E01 stack was removed with
`docker compose -f infra/e01.compose.yaml down -v`; no matching container,
volume, or network remained afterward.

## A03 Patroni/HA

Started the dedicated Patroni lab with the existing etcd 3.5.17 executable and
ran the live probe and versioned replays **serially** to avoid sharing the lab
network between concurrent fault injections.

The direct probe returned:

```text
acknowledged_lost=0, new=p1, old=p2, old_process_alive=true,
old_write_rejected=true, rejoin="basebackup via Patroni reinitialize",
rto_seconds=20.843
```

Live replay results were:

```text
v2: live_executed=true, acknowledged_lost=0, old_write_rejected=true,
    rejoin=basebackup via Patroni reinitialize, rto_seconds=21.791
v3: live_executed=true, acknowledged_lost=0, old_write_rejected=true,
    rejoin=basebackup via Patroni reinitialize, rto_seconds=22.832
v4: live_executed=true, acknowledged_lost=0, old_write_rejected=true,
    rejoin=basebackup via Patroni reinitialize, rto_seconds=22.301
```

The combined live test command also passed:

```text
A03_PATRONI_LIVE=1 ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd \
  uv run pytest tests/recovery/ha/test_patroni_probe.py \
    tests/recovery/ha/test_a03.py -q
......                                                                   [100%]
6 passed in 32.44s
```

After the run, `ETCD_BINARY=... bash infra/a03-patroni/lab.sh down` removed
both Patroni containers, both data volumes, the Compose network, and the
local etcd container. A Docker listing found no matching A03 containers,
volumes, or network.

## Verdict

**PASS.** E01's eight PostgreSQL-backed tests and A03's direct probe, three
live versioned replays, and six-test HA suite were independently reproduced.
The fence replays are included in the listed suites. Results describe local
disposable PostgreSQL/Patroni services; they do not establish independent-host
HA or production RTO/RPO guarantees. No implementation, tutorial, plan,
progress, or index file was changed.
