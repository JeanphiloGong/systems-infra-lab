# Q04 v2：普通刷新和并发刷新，对读者的影响不同 plan

Prerequisite: the preceding version's frozen result.

Pressure / Naive / Break: v1 only refreshes after the fact. The pressure is reader behavior during refresh and PostgreSQL's CONCURRENTLY prerequisites. The deterministic break records missing-index and unpopulated-view SQLSTATEs before successful concurrent refresh.

Change: Create the unique index and populated materialized view required by CONCURRENTLY, run the refresh path, and read from a separate connection while checking exact errors.

Check: uv run python -m labs.query.derived.v2; uv run python tests/query/derived/replay_q04.py --version 2; expected observation: missing_index_sqlstate and unpopulated_sqlstate are returned; reader sees 300050 before and after refresh.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/04-derived/v2/tutorial.md` and the extracted replay output. Still-lacks: The single-node experiment does not prove zero blocking under production load.

Next: v3 adds cache-aside TTL semantics.
