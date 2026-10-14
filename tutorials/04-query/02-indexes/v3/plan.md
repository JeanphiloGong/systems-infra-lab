# Q02 v3: An Index Only Scan may still visit the heap plan

Prerequisite: the preceding version's frozen result.

Pressure / Naive / Break: v2 compares composite indexes but does not expose heap visibility. The break updates indexed rows, then compares visible, updated, and vacuumed plans. All return the same changed rows.

Change: Run VACUUM/visibility preparation, update rows, and vacuum again; inspect Index Only Scan heap_fetches before and after. The mechanism is visibility-map state, not a new index type.

Check: uv run python postgres.py; uv run python tests/query/indexes/replay_q02.py --version 3; expected observation: visible and vacuumed heap_fetches=0, updated heap_fetches>0, and changed rows equal expected.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/02-indexes/v3/tutorial.md` and the extracted replay output. Still-lacks: The checkpoint controls one table and does not claim universal index-only performance.

Next: Q03 measures planner estimates and Q04 covers derived read models.

Source-of-truth: the v3 tutorial fence is also frozen as `labs/query/indexes/checkpoints/v3.py`; replay compares the versioned checkpoint before executing it.
