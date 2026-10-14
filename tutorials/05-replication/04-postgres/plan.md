# R04 tutorial plan

Use a dedicated PostgreSQL 16 stack and real SQL checks.

1. v0: pg_basebackup and streaming WAL. Wait for a primary LSN on the standby, query pg_stat_replication, and prove standby writes fail.
2. v1: publish only orders and observe initial copy plus INSERT/UPDATE/DELETE; unpublished remains absent.
3. v2: compare physical DDL, logical DDL, sequences, and replica identity with PostgreSQL 16.
4. v3: disable the consumer, measure replication-slot retained WAL, write 20,000 rows, re-enable, and verify catch-up lowers retention.

Each version includes complete Python/config/script fences. Replay writes those fences to a temporary package, checks exact source equality, and runs against the dedicated services. Cleanup is limited to docker compose -f infra/r04.compose.yaml down -v.
