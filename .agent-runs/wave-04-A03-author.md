# A03 author evidence

The fixed-member model is in `labs/recovery/ha/model.py`; v0-v4 tutorial fences replay in fresh temporary directories.

```text
$ uv run pytest tests/recovery/ha -q
5 passed
$ uv run python tests/recovery/ha/replay_a03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

Disposable PostgreSQL physical promotion was run with `infra/r04.compose.yaml`:

```text
$ docker compose -f infra/r04.compose.yaml up -d --wait
$ A03_POSTGRES_LIVE=1 uv run python -m labs.recovery.ha.postgres_probe
{"old_primary_fence_required": true, "replica_promoted": true, "rows": [[1, "before-promotion"], [2, "after-promotion"]]}
$ docker compose -f infra/r04.compose.yaml stop primary
old primary fenced: connection refused after promotion
```

Patroni v2-v4 was then verified with the dedicated `infra/a03-patroni` stack. The image pins PostgreSQL 16 and Patroni 4.1.5 with `psycopg[binary]==3.3.6`; the disposable etcd control node was etcd 3.5.17.

```text
$ ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd bash infra/a03-patroni/lab.sh up
$ uv run python -m labs.recovery.ha.patroni_probe
{"acknowledged_lost": 0, "client_attempts": 81, "cutback_seconds": 2.086, "new": "p2", "old": "p1", "old_process_alive": true, "old_write_rejected": true, "rejoin": "basebackup via Patroni reinitialize", "rto_seconds": 21.06}
$ bash infra/a03-patroni/lab.sh down
```

The live run disconnected only the old primary's Docker network. Patroni promoted the other node, retained the explicitly acknowledged row, rejected a local write on the isolated old primary while its container process remained alive, rebuilt that node with `reinitialize`, and completed a planned switchover/cutback. The measured RTO and retry count are one run's observations, not service-level objectives. RPO zero applies only because the probe waited for the sample row to reach the replica before failure; asynchronous replication does not guarantee zero loss. A single etcd instance is an experiment control point, not a production HA DCS topology, and Patroni fencing is not hardware STONITH.

The v2-v4 source replay scripts extract all five fenced files into a fresh temporary directory and verify exact source equality. They intentionally report `live_required: true` instead of starting Docker from an isolated copy; run the live probe only against the explicitly started disposable stack.

The corrected deterministic runner now extracts and executes the additional
model/experiment fences for v2-v4 as well as the frozen v0-v1 checkpoints:

```text
$ uv run python tests/recovery/ha/replay_a03.py
v0 replay ok: {'rpo_rows': {'order': 'one'}, 'rto_window': 3}
v1 replay ok: {'confirmed': {'order': 'two'}, 'primary': 'b'}
v2 replay ok: {'automatic_primary': 'b', 'generation': 2}
v3 replay ok: {'new_value': 'two', 'old_primary_fenced': True}
v4 replay ok: {'cutover_primary': 'a', 'rows': {'order': 'three'}}
```

This command verifies teaching-model behavior only. It does not execute Patroni
or substitute for the live-process evidence above.
