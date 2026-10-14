# R04 build evidence

Status: implemented; independent review required. No commits and no docs/progress.md changes.

Dedicated compose project systems-r04 owns primary 55440, physical standby 55441, logical subscriber 55442, three named volumes, and setup scripts. Existing shared PostgreSQL and pgbouncer were not changed. Image is pinned PostgreSQL 16 digest. Primary has wal_level=logical, max_replication_slots=8, max_wal_senders=8.

Roadmap coverage: v0 real WAL LSN wait, physical row replication, streaming state, recovery state, standby write rejection. v1 real selected publication and INSERT/UPDATE/DELETE. v2 physical DDL reaches standby while logical DDL does not; sequence last_value diverges; REPLICA IDENTITY NOTHING rejects UPDATE and FULL permits it after schema alignment. v3 disables the logical subscription, observes inactive slot, inserts 20,000 rows, measures retained bytes increasing, then re-enables and observes catch-up and retention decrease.

Environment and cleanup:

```bash
docker compose -f infra/r04.compose.yaml up -d
export R04_DATABASE_URL='postgresql://r04:r04_local_only@127.0.0.1:55440/r04'
R04_DATABASE_URL="$R04_DATABASE_URL" uv run python -m pytest tests/replication/postgres -q
docker compose -f infra/r04.compose.yaml down -v
```

Verified while the dedicated services were running: R04_DATABASE_URL=postgresql://r04:r04_local_only@127.0.0.1:55440/r04, `uv run python -m pytest tests/replication/postgres -q` => 5 passed in 3.12s. All Python fences were extracted to an empty temporary package and checked byte-for-byte against labs/replication/postgres sources before real execution. Four tests execute v0-v3 and one checks all complete source fences. Without the dedicated stack and R04_DATABASE_URL, the four database tests are intentionally blocked rather than mocked.

Observed v3 values: paused_bytes=56, retained_bytes=2,832,528, recovered_bytes=0, subscriber_rows=20,001. This is slot retention distance, not total disk usage. All three containers share one host, so this is not independent-host failover evidence. No production credentials, global cleanup, or shared server mutation.
