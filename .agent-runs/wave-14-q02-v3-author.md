# Wave 14 Q02 v3 author evidence

Date: 2026-10-14. Scope: Q02 v3 visibility-map experiment, its matching tutorial fence, live regression assertion, and this record. No docs/progress/index changes.

## Reproduced failure

The independent review failure was reproducible with PostgreSQL 16: after updating the indexed rows, ordinary `VACUUM (ANALYZE)` left `measure(plans["vacuumed"])["heap_fetches"]` positive. The original assertion `== 0` therefore failed; the target behavior was not relaxed.

## Minimal repair

The fixture now keeps ordinary `VACUUM (ANALYZE)` before the first visible scan, then uses an explicit `VACUUM (FULL, ANALYZE)` rewrite followed by `VACUUM (ANALYZE)` after the update. The full rewrite is a deliberate disposable-table preparation step that makes all-visible state deterministic on the observed service. The source and tutorial `postgres.py` fences are synchronized. `tests/query/indexes/test_postgres.py` now asserts visible heap fetches `0`, updated heap fetches `>0`, and vacuumed heap fetches `0` for version 3.

## Verification

- Live PostgreSQL test: `SYSTEMS_LAB_DATABASE_URL=... uv run pytest tests/query/indexes/test_postgres.py -q` -> **4 passed**.
- Full live replay: `SYSTEMS_LAB_DATABASE_URL=... uv run python tests/query/indexes/replay_q02.py` -> v0, v1, v2, v3 all passed. v3 observed `visible.heap_fetches=0`, `updated.heap_fetches=200`, `vacuumed.heap_fetches=0`.
- Extracted v3 replay: `... uv run python tests/query/indexes/replay_q02.py --version 3` -> passed with the same boundary.
- Fence/local tests: `uv run pytest tests/query/indexes/test_q02_indexes.py -q` -> **2 passed**.

The shared isolated PostgreSQL container was already running and was left available for the surrounding query wave; no unrelated compose stack was stopped. No new abstraction was added; the change is a permanent experiment-preparation step and regression assertion.
