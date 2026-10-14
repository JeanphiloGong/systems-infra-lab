# Q04 v3：Cache-aside：先定义过期边界，再谈命中率 plan

Prerequisite: the preceding version's frozen result.

Pressure / Naive / Break: v2 governs a database view, not an application cache. The pressure is a TTL boundary: two reads hit the cache, then expiry loads fresh source data after a +50 change.

Change: Use the deterministic clock/cache fence: load 300000, hit twice, advance past expiry, then load 300050. Count source loads and hits rather than claiming a latency benchmark.

Check: uv run python -m labs.query.derived.v3; uv run python tests/query/derived/replay_q04.py --version 3; expected observation: source_loads=2, cache_hits=2, before_expiry=300000, after_expiry=300050.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/04-derived/v3/tutorial.md` and the extracted replay output. Still-lacks: This cache is in-process and has no distributed invalidation or stampede control.

Next: v4 protects against an expired reader filling the cache with an old result.
