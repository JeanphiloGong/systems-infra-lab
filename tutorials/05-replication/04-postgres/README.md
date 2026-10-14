# R04: PostgreSQL physical and logical replication

This tutorial owns one PostgreSQL 16 stack in infra/r04.compose.yaml: primary 55440, physical standby 55441, and logical subscriber 55442. Do not connect to shared port 55432. All tables, publications, subscriptions, slots, and data belong to this stack.

## Start and clean up

```bash
docker compose -f infra/r04.compose.yaml up -d
docker compose -f infra/r04.compose.yaml ps
export R04_DATABASE_URL='postgresql://r04:r04_local_only@127.0.0.1:55440/r04'
uv sync
R04_DATABASE_URL="$R04_DATABASE_URL" uv run python -m pytest tests/replication/postgres -q
```

Wait for the standby to finish pg_basebackup and accept connections. Scripts use the fixed loopback ports; the environment variable makes the test fail if the dedicated service was not selected. The password is local-only.

```bash
docker compose -f infra/r04.compose.yaml logs --tail 30 standby
docker compose -f infra/r04.compose.yaml down -v
```

`down -v` removes only the systems-r04 services and volumes. Do not run global volume pruning.

## Checkpoints

- [v0](v0/tutorial.md): physical streaming, WAL LSN progress, read-only standby, and streaming sender state.
- [v1](v1/tutorial.md): selected logical publication with INSERT, UPDATE, DELETE propagation.
- [v2](v2/tutorial.md): physical versus logical DDL, sequence divergence, and replica identity behavior.
- [v3](v3/tutorial.md): paused logical consumer, retained WAL bytes, and recovery after re-enable.

The experiments use real fixed PostgreSQL 16 behavior. They do not implement automatic failover or claim independent host failure. WAL byte distance is a replication-slot indicator, not complete disk usage; checkpoints, archives, and other slots also matter.
