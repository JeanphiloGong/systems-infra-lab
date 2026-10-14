# T04 v0 计划

列出 doctor1/doctor2 两个串行顺序，最终始终一人值班，作为并发实验参考集合。下一版用真实 SERIALIZABLE 验证不可串行历史会被中止。


## Tutorial Increment

- **Pressure:** The a constrained appointment or on-call roster scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 两位医生都在岗。串行执行医生1下班后医生2看到只剩一人并拒绝，或反过来；合法最终状态是恰好一人值班。 serial_results = {(False, True), (True, False)}
- **Change:** # T04 v0：先定义串行参考; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/serializable -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T04 serializability teaching model for a constrained appointment or on-call roster; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of T04 serializability, carrying forward the state and invariant rather than restarting from a disconnected example.

