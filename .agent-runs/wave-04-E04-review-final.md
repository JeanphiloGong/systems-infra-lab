# E04 analytics review: PASS

Independent review ran the dedicated three-node PostgreSQL 16 stack from
`labs/dataflows/analytics/compose.yaml` and then cleaned it with `down -v`.

Observed command sequence: `docker compose -f labs/dataflows/analytics/compose.yaml up -d --wait`; `E04_LIVE=1 uv run pytest -q tests/dataflows/analytics/test_e04_replay.py` -> **8 passed in 10.69s**; `docker compose -f labs/dataflows/analytics/compose.yaml down -v`.

The four exact extraction tests copied every version's `vN.py`, `pg.py`, and
`compose.yaml` fences into a temporary directory, checked exact source equality,
and verified the complete dependency set. The four live tests executed those
extracted implementations against the running stack.

Observed acceptance behavior:

- v0 persisted both source-scoped batch records and provenance, loaded 100
  rows from each source, and produced the warehouse report.
- v1 replayed both sources idempotently, applied order and customer late
  corrections, preserved source-scoped lineage, and converged the copied
  report.
- v2 executed a real `postgres_fdw` join across independent source servers;
  unrestricted reads transferred 200 rows, the selective join transferred 6,
  and each source scan covered 100 rows.
- v3 observed an orphan during independent source drift, restored a customer
  and converged, stopped the customer process to produce SQLSTATE `08001`,
  preserved the warehouse foreign-server configuration, kept copied data
  available, and verified post-catch-up convergence.

The tutorial and implementation state the scope limits: no distributed
transaction or global snapshot claim. Decision: **PASS**. No abstraction was
added and no implementation cleanup was required.
