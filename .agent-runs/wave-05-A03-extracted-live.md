# A03 extracted live execution

Coordinator verification, 2026-10-14. This proves the extracted live probe runs;
it does not close the independent review's tutorial progression findings.

Started dedicated infrastructure with:

```sh
ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd bash infra/a03-patroni/lab.sh up
```

Executed sequentially, each with exit code 0:

```sh
uv run python tests/recovery/ha/replay_patroni.py --version 2 --live
uv run python tests/recovery/ha/replay_patroni.py --version 3 --live
uv run python tests/recovery/ha/replay_patroni.py --version 4 --live
```

The runner checks fenced source equality, extracts files into a temporary
directory and executes the extracted probe with Python isolated mode.

| Version | RTO seconds | Client attempts | Cutback seconds |
| --- | --- | --- | --- |
| 2 | 23.218 | 89 | 2.099 |
| 3 | 21.567 | 83 | 2.089 |
| 4 | 21.113 | 81 | 2.087 |

All three reported `live_executed: true`, old=p1, new=p2,
`acknowledged_lost: 0`, `old_process_alive: true`,
`old_write_rejected: true`, and rejoin by Patroni basebackup reinitialize.
These are single-host observations with a pre-caught-up sample, not general
asynchronous replication RPO guarantees. All versions still contain the same
full live scenario; distinct incremental teaching remains unverified.

Cleanup: `bash infra/a03-patroni/lab.sh down` exited 0, removing both
PostgreSQL containers, both data volumes, the dedicated network and etcd container.
