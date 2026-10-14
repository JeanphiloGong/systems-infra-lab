# Q04 v1：物化视图能省查询工作，却不会自动变新 plan

Prerequisite: the preceding version's frozen result.

Pressure / Naive / Break: v0 recomputes every read. The pressure is freshness after a source insert: a materialized daily view remains 300000 while source is 300050 until refreshed.

Change: Create the materialized view, insert 50, read before/after refresh, and assert the stale and fresh values from PostgreSQL.

Check: uv run python -m labs.query.derived.v1; uv run python tests/query/derived/replay_q04.py --version 1; expected observation: before=stale=300000, fresh=after_refresh=source=300050.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/04-derived/v1/tutorial.md` and the extracted replay output. Still-lacks: Refresh locking and concurrent refresh are deferred; the view has no automatic invalidation.

Next: v2 compares ordinary refresh with CONCURRENTLY and its prerequisites.
