# Q02 v2: Compare column order with the same range and sort plan

Prerequisite: the preceding version's frozen result.

Pressure / Naive / Break: v1 shows a single-column index choice but not composite ordering. The pressure is a time range ordered by user_id and created_at. The break runs identical results through user_time and time_user indexes and compares buffer accesses.

Change: Add the two composite indexes, run the same bounded query, and measure plan nodes and buffers. Preserve result equality before comparing work.

Check: uv run python postgres.py; uv run python tests/query/indexes/replay_q02.py --version 2; expected observation: all four plans return expected rows; each indexed plan has Index; user_time buffer_accesses < time_user.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/02-indexes/v2/tutorial.md` and the extracted replay output. Still-lacks: Buffer counters are PostgreSQL shared-block observations, not device bytes or stable latency.

Next: v3 observes visibility-map effects on Index Only Scan.

Source-of-truth: the tutorial checkpoint must equal `labs/query/indexes/checkpoints/v2.py`; `tests/query/indexes/replay_q02.py --version 2` compares those files before executing the extracted checkpoint.
