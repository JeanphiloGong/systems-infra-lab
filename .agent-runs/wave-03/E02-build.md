# E02 schema-evolution build evidence

E02 implements a real PostgreSQL 16 schema migration on the dedicated `infra/e02.compose.yaml` service at port 55451. The scenario changes `profiles.name` to `profiles.full_name` through four executable tutorial checkpoints.

- v0 directly renames the column and proves an old `SELECT name` client receives `UndefinedColumn`.
- v1 adds nullable `full_name`; old reads remain valid, new reads use `COALESCE`, and the transition write updates both columns.
- v2 backfills historical rows in committed batches with fresh worker processes. The first worker commits two rows then exits; the second exits inside an uncommitted batch and leaves both rows and checkpoint unchanged; a third worker resumes and fills two remaining rows, while a protected new-client value is preserved; a fourth fresh worker does zero work.
- v3 verifies all rows are populated before setting `NOT NULL` and dropping `name`; the old query is rejected and the new column remains readable.

Validation:

```bash
docker compose -f infra/e02.compose.yaml up -d --wait
E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run python -m pytest tests/dataflows/schema_evolution -q
docker compose -f infra/e02.compose.yaml down -v
```

Result: **5 passed in 2.77s** after the fresh-worker failpoint revision. Each v0-v3 chapter extracts complete `common.py` and version fences into a fresh temporary package, checks exact source equality, and executes against isolated PostgreSQL. No progress file or commit was changed.

Permanent teaching code consists of the direct PostgreSQL connection/reset helper and the v2 batch backfill function. No compatibility wrapper or migration shim was added; the dual-write behavior is intentionally shown only at the transition checkpoint.
