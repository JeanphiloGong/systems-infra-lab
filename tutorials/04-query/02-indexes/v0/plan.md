# Q02 v0: Without an index, count the work plan

Prerequisite: PostgreSQL 16 isolated query stack and the module scenario.

Pressure / Naive / Break: The baseline query filters a 100000-row orders table by user_id=7 with no usable secondary index. The naive plan is a sequential scan; the deterministic break is EXPLAIN ANALYZE on the baseline table, which must report Seq Scan while returning the expected rows.

Change: Create the isolated q02 schema and measure plan nodes, buffers, estimated rows, actual rows, and elapsed time with PostgreSQL EXPLAIN ANALYZE. Do not infer device I/O from shared blocks.

Check: uv run python postgres.py; uv run python tests/query/indexes/replay_q02.py --version 0; expected observation: assert "Seq Scan" in measure(plans["baseline"])["nodes"] and query rows equal expected.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/02-indexes/v0/tutorial.md` and the extracted replay output. Still-lacks: A secondary index has not been added, and this does not establish a speedup or CPU measurement.

Next: v1 adds an index and compares selective versus common predicates.

Source-of-truth: the tutorial checkpoint must equal `labs/query/indexes/checkpoints/v0.py`; `tests/query/indexes/replay_q02.py --version 0` compares those files before executing the extracted checkpoint.
