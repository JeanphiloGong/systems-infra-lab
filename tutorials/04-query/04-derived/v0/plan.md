# Q04 v0：每次现场汇总，先建立答案基准 plan

Prerequisite: PostgreSQL 16 isolated query stack and the module scenario.

Pressure / Naive / Break: A dashboard needs daily totals from 30 days of 10000 rows. The naive implementation executes the aggregate twice; the deterministic baseline must return identical 30-row answers and expose two query plans/cost summaries.

Change: Run the real PostgreSQL aggregate twice and retain the plan summaries as the comparison baseline.

Check: uv run python -m labs.query.derived.v0; uv run python tests/query/derived/replay_q04.py --version 0; expected observation: first == second == [(day,10000) for day in range(30)] and queries=2.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/04-derived/v0/tutorial.md` and the extracted replay output. Still-lacks: No materialized state or cache exists; elapsed milliseconds are sample measurements.

Next: v1 materializes the result and demonstrates staleness.
