# E01 build evidence

E01 implemented under labs/dataflows/cdc and tutorials/08-dataflows/01-cdc against real PostgreSQL 16 logical decoding, not a dictionary simulation. Dedicated infra/e01.compose.yaml owns one pinned primary at 127.0.0.1:55450 with wal_level=logical and eight replication slots; shared/R04 services are untouched.

- v0 reproduces dual-write inconsistency between source_orders and projection.
- v1 creates test_decoding slot and captures committed INSERT/UPDATE/DELETE text with LSN rows.
- v2 creates slot before snapshot, reads snapshot, consumes post-snapshot insert, and deduplicates overlapping source ids.
- v3 writes projection and consumer checkpoint in one SQLite transaction; replaying one change is idempotent.
- v4 pauses slot by withholding reads, writes 20,000 rows, observes retained WAL distance and >20,000 events, then consumes changes and verifies confirmed_flush_lsn advances. The retained byte value is a slot indicator, not total disk size.

Validation while dedicated E01 service was running:

```bash
docker compose -f infra/e01.compose.yaml up -d
E01_DATABASE_URL='postgresql://e01:e01_local_only@127.0.0.1:55450/e01' uv run python -m pytest tests/dataflows/cdc -q
docker compose -f infra/e01.compose.yaml down -v
```

Result: **6 passed in 2.29s**. Replay extracts common.py and each version source from complete Markdown fences, checks exact equality with labs/dataflows/cdc files, runs each in an isolated temporary package against PostgreSQL, and asserts semantic output. All cleanup is project-scoped compose down -v; no shared progress edits or commits.

Limits: test_decoding textual format and WAL slot fields are PostgreSQL 16 behavior; no global order across unrelated streams is claimed. The slot replay uses SQL polling rather than a production connector, and v3's SQLite projection is a deterministic transaction stand-in for a target that supports atomic checkpointing. Production credentials, transport security, connector failover and schema registries are outside this checkpoint.
