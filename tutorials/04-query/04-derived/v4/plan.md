# Q04 v4：失效之后，旧查询还可能把缓存填脏 plan

Prerequisite: the preceding version's frozen result.

Pressure / Naive / Break: v3 defines TTL but an in-flight old query can finish after expiry. The deterministic barrier makes a stale writer pause while a fresh writer stores 300050; the stale fill must be rejected by generation/expiry state.

Change: Run the captured concurrent reader/writer sequence for both stale and fresh outcomes, then assert the cache value remains fresh and rejected_fills=1 where the stale result loses.

Check: uv run python -m labs.query.derived.v4; uv run python tests/query/derived/replay_q04.py --version 4; expected observation: actual=300050; returned/before_expiry/after_expiry follow the branch; rejected_fills=1 in stale-fill branch.

Freeze: the complete source-matching checkpoint fences in `tutorials/04-query/04-derived/v4/tutorial.md` and the extracted replay output. Still-lacks: The generation fence is local to this cache and does not provide cross-process coherence.

Next: The Q04 module ends at an explicit cache invalidation contract; production distribution is deferred.
