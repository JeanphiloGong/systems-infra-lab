# T04 v1 计划

使用 Barrier 协调两个 `SERIALIZABLE` 事务同时读取；一方被 `SerializationFailure` 中止，另一方提交。测试只断言一个失败与最终至少一人值班，不固定胜者。完整入口包含 schema 初始化与清理。


## Tutorial Increment

- **Pressure:** The a constrained appointment or on-call roster scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** T02 的 RR 允许两个医生都下班；`SERIALIZABLE` 要求已提交历史等价某个串行执行。两个事务由 `Barrier` 同时读取，然后更新不同医生；数据库中止一方，异常离开事务块后此前更新全部回滚。 完整 checkpoint 是 `labs/transactions/serializable/serializable.py`，并由 `schema.sql` 初始化两行医生。运行：
- **Change:** # T04 v1：SERIALIZABLE 会拒绝不可串行历史; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/serializable -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T04 serializability teaching model for a constrained appointment or on-call roster; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of T04 serializability, carrying forward the state and invariant rather than restarting from a disconnected example.

