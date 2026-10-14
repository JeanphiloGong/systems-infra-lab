# S07 v4 计划

前置v3；目标autovacuum触发依赖阈值与后台调度，观测必须设置超时并报告未观察到。完整automatic.py作为checkpoint，真实PostgreSQL测试与独立重放；只创建并清理s07_ schema。不提交Git。


## Tutorial Increment

- **Pressure:** The updates that leave dead PostgreSQL tuples scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置v3。实验只连接本仓库PostgreSQL临时实例并创建唯一s07_ schema。逻辑COUNT与pg_stat统计分开记录；统计刷新和后台调度均有近似性，不能把一次观测推广到所有MVCC数据库。 完整 `labs/storage/vacuum/automatic.py`：
- **Change:** # S07 v4：autovacuum触发依赖阈值与后台调度，观测必须设置超时并报告未观察到; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/vacuum -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S07 vacuum teaching model for updates that leave dead PostgreSQL tuples; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

