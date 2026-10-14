# Wave 15 Q02 checkpoint fidelity evidence

Date: 2026-10-14. Scope: Q02 historical checkpoint fidelity. Added `labs/query/indexes/checkpoints/v0.py` through `v3.py`, changed `tests/query/indexes/replay_q02.py` to compare each tutorial fence byte-for-byte with its matching versioned checkpoint before execution, and updated Q02 v0-v3 plan freeze/source-of-truth notes. No other module, progress, index, or implementation behavior was changed beyond the existing v3 visibility repair.

The merged `labs/query/indexes/postgres.py` is no longer treated as the historical source for replay. Each version's tutorial fence is the teaching artifact and its matching `checkpoints/vN.py` is the frozen executable source. v0-v2 preserve their historical plan behavior; v3 contains the repaired `VACUUM (FULL, ANALYZE)` plus final `VACUUM (ANALYZE)` preparation.

Verification against the isolated PostgreSQL 16 service:

- `SYSTEMS_LAB_DATABASE_URL=... uv run python tests/query/indexes/replay_q02.py`: v0, v1, v2, and v3 all passed with source-fidelity comparisons. v3 observed visible heap fetches 0, updated 200, vacuumed 0.
- `SYSTEMS_LAB_DATABASE_URL=... uv run pytest tests/query/indexes -q`: **6 passed in 2.85s**.
- The replay path extracts and executes the versioned checkpoint only after comparing it with that version's tutorial fence. All four checkpoint paths exist.

Resource note: the PostgreSQL container used for this query wave was already a shared `systems-infra-lab-postgres-1` service and remains running to avoid affecting unrelated query experiments. No temporary database schemas survive: each checkpoint drops its unique q02 schema in `finally`. No cleanup command was issued against other topic services.

No new runtime abstraction was introduced beyond permanent versioned checkpoint files required to preserve tutorial history. No acceptance claim beyond the recorded author verification is made.
