# Q02 v1: A secondary index is not always cheaper plan

Prerequisite: the preceding version's frozen result.

Pressure / Naive / Break: v0 has only a sequential scan. The pressure is selectivity: user_id=7 is rare, while user_id=7 after 90,000 rows are changed is common. The deterministic break runs both predicates against the same indexed table and observes different planner choices.

Change: Create the by_user index and compare selective/index and common/sequence plans while asserting both result sets. The mechanism is PostgreSQL cost-based choice, not forcing an index.

Check: uv run python postgres.py; uv run python tests/query/indexes/replay_q02.py --version 1; expected observation: baseline has Seq Scan; selective has an Index node; common has Seq Scan; result rows match expected.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/02-indexes/v1/tutorial.md` and the extracted replay output. Still-lacks: Statistics and one PostgreSQL version are used; no workload-wide index recommendation follows.

Next: v2 compares composite index column order and buffer work.

Source-of-truth: the tutorial checkpoint must equal `labs/query/indexes/checkpoints/v1.py`; `tests/query/indexes/replay_q02.py --version 1` compares those files before executing the extracted checkpoint.
