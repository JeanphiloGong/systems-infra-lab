# A01 backup/PITR review: PASS

Static review and source replay checks passed. `A01_DATABASE_URL=... uv run
pytest -q tests/recovery/backup -k exact_python_fences` passed, confirming all
v0-v4 tutorial fences match `common.py` and their corresponding implementation
source. The implementation uses plain SQL restore, custom-format restore,
truncated-dump failure, physical base backup plus WAL target recovery, and
missing-archive target failure as described in the supplied build evidence.

The first local attempt found no service on `127.0.0.1:55452`. Root then
independently ran the disposable stack and the full command, obtaining `6
passed in 19.15s`, followed by `docker compose -f infra/e03.compose.yaml down
-v`. This directly observed all five version checks, including separate
target-time recovery and the missing-WAL failure.

Decision: **PASS**. No implementation changes are requested from this review.
