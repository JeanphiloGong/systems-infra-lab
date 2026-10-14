# A01 scope repair author evidence

Date: 2026-10-14. Repository: `/home/gong/date/2026/oct/systems-infra-lab`.

Scope changed: A01 `common.py`, v0/v1/v2/v3/v4 source fences, v0-v4 tutorials and plans, and `tests/recovery/backup/test_a01_replay.py`. No progress/index/shared infrastructure changes were made. The dedicated `infra/e03.compose.yaml` stack was used and then removed with `docker compose -f infra/e03.compose.yaml down -v`.

Implemented scope:

- v0 creates a unique restore database, imports plain SQL there, keeps the source intact, checks `id`/`balance` NOT NULL metadata, and observes duplicate key `23505` and NULL `23502` failures.
- v1 imports the custom archive into a unique independent target while the source retains its post-backup `(3,50)` row.
- v2 preserves the truncated logical-archive corruption experiment and additionally creates a physical base backup, records start/end LSN, waits for every required segment in that interval, and returns the actual segment names and 16 MiB checks.
- v3 retains target-time PITR and now uses the required WAL interval rather than one selected segment.
- v4 performs a successful target recovery with monotonic elapsed time, a broken-archive failed attempt with its elapsed time, and reports the acknowledged pre-target set plus a post-target committed row that is absent from target recovery.

Live author commands:

- v0 extracted replay: **1 passed**.
- v2 extracted replay: **1 passed in 1.88s**; this included the physical base backup, real WAL archive interval and corruption branch.
- v3/v4 recovery-container invocations timed out in the current Docker environment before test output was returned. No A01 recovery container remained afterward. These versions are not claimed accepted; rerun is required before closure.

Follow-up interval repair: the first v3/v4 failure was reproduced by the independent run as missing interior WAL segments (for example `000000010000000000000004` and `...000006`, and v4 `...000008`). `wait_archived_segments` was then changed to enumerate every hexadecimal segment between the start and end LSN, reject timeline/wrap crossings, force a WAL switch, and wait up to 90 seconds for every 16 MiB file. This preserves interval continuity instead of reducing the check to endpoints. All tutorial common.py fences were synchronized after the helper change.

After that repair, v3 and v2 attempts again reached the recovery-container phase but did not return test output within the tool's 30-second polling window; the dedicated stack was explicitly brought down with `docker compose -f infra/e03.compose.yaml down -v`. The environment currently has no A01 recovery container. Because a clean post-repair v3/v4 result was not observed, the repair remains pending independent rerun and no acceptance claim is made.

The source/tutorial fences were synchronized and the test continues to assert exact fence equality. The full test file also asserts v0 SQLSTATEs, v2 required segment evidence, v3 archive continuity, and v4 measured durations/data-loss fields. No new general-purpose abstraction was added; `independent_database` and `wait_archived_segments` are permanent A01 helpers required by the scope. No temporary files or containers remain from the dedicated stack.

## WAL filename regression and rerun

The reproduced defect was the segment formatter producing a truncated suffix (`:08X`), for example `0000000100000002`, while PostgreSQL filenames require the 16-hex-digit suffix (`000000010000000000000002`). A regression test was added before the implementation change and initially failed during collection because `wal_segment_names` did not exist. The helper now returns every segment with `:016X`, rejects timeline/wrap crossings, and is used by `wait_archived_segments`; all v0-v4 tutorial common.py fences were synchronized.

After the fix:

- `test_wal_segment_names_preserve_postgresql_16_digit_suffix` and exact-fence checks: **2 passed**.
- v2 extracted live replay: **1 passed in 1.69s**.
- v3 extracted live replay: **1 passed in 6.02s**.
- v4 extracted live replay: **1 passed in 14.84s**, including successful and broken-archive elapsed measurements and the data-loss window.
- Full `A01_DATABASE_URL=... uv run pytest tests/recovery/backup -q`: **7 passed in 25.04s**.

The dedicated PostgreSQL stack was stopped with `docker compose -f infra/e03.compose.yaml down -v`; no A01 containers remain. The corrected interval check remains inclusive of every required WAL segment; it was not weakened to endpoint or single-segment validation.
