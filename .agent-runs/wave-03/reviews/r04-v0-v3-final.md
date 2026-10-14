# R04 independent PostgreSQL replication review

Verdict: PASS against the original `docs/roadmap.md:375` scope, within the documented single-host Docker demonstration boundaries. No blocking findings.

## Actual verification

Started from the author-provided dedicated stack (primary `55440`, physical standby `55441`, logical subscriber `55442`) and ran:

`R04_DATABASE_URL='postgresql://r04:r04_local_only@127.0.0.1:55440/r04' uv run python -m pytest tests/replication/postgres -q`

Result: **5 passed in 3.33s**. Four cases extracted and executed the printed v0-v3 dependencies in fresh temporary package directories, with isolated PYTHONPATH and real PostgreSQL connections. The fifth test verified expected complete Python fences. Independently compared all **10 Python fences** in the four tutorials to their source files byte-for-byte. After verification, removed only the owned stack and volumes with `docker compose -f infra/r04.compose.yaml down -v`.

## Roadmap evidence

- v0 obtains a primary WAL LSN, waits until `pg_last_wal_replay_lsn()` on the standby reaches it, reads the streamed row, checks `pg_is_in_recovery()`, rejects a standby write, and observes `pg_stat_replication` in `streaming` state.
- v1 creates a real selected-table publication/subscription. INSERT, UPDATE and DELETE propagate; an unpublished table is absent from the subscriber.
- v2 demonstrates physical versus logical DDL with actual nodes: `ALTER TABLE` appears on the physical standby but not the logical subscriber. The tutorial manually aligns the logical schema before an INSERT, then observes independently drifting identity sequences (`primary=2`, `subscriber=1`) and a real subscriber sequence collision. `REPLICA IDENTITY NOTHING` rejects UPDATE; `FULL` permits subsequent update/delete propagation.
- v3 disables the subscription, confirms its slot is inactive, inserts 20,000 rows, and measures slot-retained WAL increasing from **56 bytes** to **2,832,528 bytes**. Re-enabling catches the subscriber to **20,001 rows** and decreases retained bytes to zero/less than the paused maximum. This ties paused consumer progress to WAL retention distance, not a fabricated total disk-usage claim.

## Boundaries retained

All three PostgreSQL containers share one host and use a pinned PostgreSQL 16 image; this is not independent-host failover or production durability evidence. v2's logical DDL result is for the selected publication/schema and deliberately requires manual subscriber schema alignment. Sequence values are not replicated as a general guarantee. v3 measures one logical replication slot's retained WAL, not filesystem growth or disk capacity. Tests use polling and bounded waits, and cleanup is limited to the dedicated compose project.

Review artifact only; no implementation abstraction or source cleanup added.
