# E02 original-scope revision evidence

Author run: 2026-10-14, `/home/gong/date/2026/oct/systems-infra-lab`.

Changed only E02 common.py, v0-v3.py, v0-v3 tutorial/plan documents, test_e02_replay.py, and this record. Module plan supplied by root was read, not overwritten; progress and indexes were not edited.

## Executed evidence

`docker compose -f infra/e02.compose.yaml up -d --wait` created a healthy dedicated PostgreSQL container on localhost:55451.

`E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest tests/dataflows/schema_evolution -q` returned **6 passed in 5.31s**. Each live test extracts its two complete fences into a temporary directory, checks exact source equality, and launches a fresh interpreter there. These are author results, not independent acceptance.

- v0: old writer missing newly required field and populated-table DDL both return 23502; old rename-read failure remains separately checked.
- v1: two connections exercise old/new insert/update/read combinations. New dual-write Ada Lovelace followed by old name=Grace exposes stale COALESCE=Ada Lovelace; authoritative name read returns Grace. NULL historical fallback returns Ada.
- v1 events: six producer/consumer pairs; old consumer rejects new-only payload; new consumer accepts old payload during transition; missing both fields rejects. Separate no-DB subprocess test executes these functions.
- v2: committed worker exits 17; precommit worker exits 19; checkpoint and first batch queried as 2; workers emit actual JSON counts 2/0 with cursor 4. Two whole experiments run consecutively on one database and return identical evidence. ID 5 remains Protected by new client. Seed/reset clears checkpoint; worker recovery does not.
- v3: active old-client gate blocks, then incomplete-backfill gate blocks. Only after both pass does contraction succeed. NULL insert, omitted field insert, and NULL update each return 23502. Final Linus insert/read succeeds. Catalog queries prove name removed, full_name NOT NULL, checkpoint and client registry removed. Final event consumer rejects old-only, absent, NULL, and empty values; it has no legacy fallback or v1 import.
- All four live versions finish with profiles/checkpoint/client-registry absent, verified by independent connections in tests.

## Operational boundaries

v2 requires old writers drained before final synchronization and cursor advancement; new writers still dual-write. The registry in v3 is an explicit controlled deployment readiness input, not an automatic service-discovery or fencing system. PostgreSQL table locks protect the contraction transaction but cannot prevent an external retired process restarting. These constraints are described in tutorial prose; required original-scope behaviors were implemented rather than replaced by limitations.

Added direct event consumer functions and the contraction operation; no reusable adapter/framework introduced. Transition reads remain only in historical v1; final v3 consumes only full_name and removes transitional database artifacts. Dedicated compose teardown runs after tests; no Git commit made.
