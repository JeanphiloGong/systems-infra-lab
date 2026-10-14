# E04 authored checkpoints awaiting independent review

Ownership: `labs/dataflows/analytics`, `tests/dataflows/analytics`, `tutorials/08-dataflows/04-analytics` and this evidence only. No commits or shared progress edits.

Read original roadmap E04 v0-v3. Implemented a fixed-version SQLite analysis/federation experiment without adding an unpinned dependency:

- v0 creates two persistent source database files, imports into a warehouse, records source batch/high watermark and verifies aggregate output.
- v1 uses source primary keys and `updated_at` to make incremental loading idempotent; a late amount correction recomputes the affected customer from source truth.
- v2 uses SQLite `ATTACH DATABASE` as the fixed federation mechanism, creates a source index, runs a selective remote predicate and reports `EXPLAIN QUERY PLAN` index use plus matching/source row counts.
- v3 compares a copied warehouse snapshot with a live federated value after a source update, then detaches the source to demonstrate copied availability versus federated failure/staleness.

Verification:

`uv run pytest tests/dataflows/analytics -q` -> **4 passed in 0.66s**. Every version extracts its complete Python fence into a fresh temporary directory, checks exact source equality and runs a new interpreter with isolated PYTHONPATH. Direct v0-v3 scripts also passed.

Observed v2 plan: `SEARCH remote.orders USING INDEX orders_region (region=?)`, 3 matching rows from 100 source rows. v3 reports copied total30 as-of2 versus live federated total60, then source unavailable after detach. Limits are explicit: small SQLite files, no enterprise warehouse scheduler, no cross-source snapshot or transaction, no production federated optimizer benchmark.
