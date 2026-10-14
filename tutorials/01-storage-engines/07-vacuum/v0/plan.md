# S07 v0 计划

反复UPDATE固定集合，ANALYZE后读取n_live_tup/n_dead_tup/物理大小并查询COUNT(*)。逻辑行数保持1000，统计显示版本回收问题；不把统计瞬间值当精确事务历史。


## Tutorial Increment

- **Pressure:** The updates that leave dead PostgreSQL tuples scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 固定1000行反复更新，业务查询仍只看到1000行，但MVCC会产生旧版本。`labs/storage/vacuum/vacuum.py` 的完整入口创建唯一schema、执行churn、ANALYZE后读取 `pg_stat_user_tables` 与关系大小，最后删除自己的schema。 完整 checkpoint：
- **Change:** # S07 v0：逻辑行数不等于旧版本数量; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/vacuum -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S07 vacuum teaching model for updates that leave dead PostgreSQL tuples; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of S07 vacuum, carrying forward the state and invariant rather than restarting from a disconnected example.

