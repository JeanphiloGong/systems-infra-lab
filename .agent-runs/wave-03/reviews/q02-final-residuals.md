# Q02 final residual review

Verdict: PASS. This follow-up resolves the two residual notes in `q02-postgres-original-scope-final.md` for the current revised tutorials.

The rare and common v1 queries now both select `id, amount` and order by `id`; only the user_id constant varies. The common result is checked against all 90,000 expected tuples, and the selective result remains checked against its pre-index baseline.

Each printed checkpoint now contains setup plus its own version's experiment only. v0 has no index branches; v1 has its secondary-index comparison; v2 has its composite-order experiment; v3 has covering-index/update/VACUUM. They no longer print future version branches. This intentionally means fences are no longer byte-identical to the multi-version worktree driver; independent execution is the relevant evidence.

Actually reran with the isolated PostgreSQL DSN:

- `uv run pytest tests/query/indexes -q`: **6 passed in 3.43s**.
- `uv run python tests/query/indexes/replay_q02.py`: all **four extracted checkpoints passed**, server **160014**.

Observed v1 rare Sort/Index Scan versus common Sort/Seq Scan with 100 versus 90,000 rows. v2 still measured 22 versus 34 buffer accesses for equal 20-row results. v3 still measured Heap Fetches 0 -> 200 -> 0. Earlier original-roadmap mapping and environment bounds continue to apply. No new blocking findings.

Review artifacts only; no implementation abstraction or source cleanup added.
