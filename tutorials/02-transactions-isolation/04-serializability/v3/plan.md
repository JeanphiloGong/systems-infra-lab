# T04 v3 写作计划

前置v2真实竞争及有界完整重试。目标记录十轮二连接竞争的吞吐、中止尝试、重试和业务决定，不承诺固定性能值。

1. 定义operations/committed/allowed/refused/aborted_attempts的计数口径，规模S，tutorial.md第1节。正常提交包含拒绝事务；异常耗尽则不返回完整报告。
2. 新增measure_once，规模M，依赖1；每轮重置两人在岗，调用concurrent_retry并累加，monotonic覆盖整个循环。解释线程和初始化开销。
3. 完整checkpoint加入--metrics入口，规模M，依赖2；从Markdown提取完整代码和schema独立运行。核对20操作/20提交、10允许/10拒绝、最终1在岗、重试至少10和正时间/吞吐。记录真实机器环境而非固定性能承诺。

不提交Git。独立review核对报告来自实际执行、v2没有提前携带metrics、严格可串行化定义包括非重叠操作实时顺序但本实验没有证明它。


## Tutorial Increment

- **Pressure:** The a constrained appointment or on-call roster scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v2完成真实中止后的重试，但一次成功不能回答重试成本。本版在同一临时schema中运行十轮相同竞争，每轮先将两人重置为在岗。模型固定两连接和两请求，目的是测量已知竞争机制，不模拟完整线上流量。 新增measure_once，rounds默认10，必须正数。每轮调用v2的concurrent_retry，因此20个业务操作最终都有数据库事务正常提交，其中10个允许下班、10个拒绝。committed包含没有UPDATE的正常拒绝事务，不能理解成20人都下班。
- **Change:** # T04 v3：让竞争成本成为可检查的报告; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/serializable -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T04 serializability teaching model for a constrained appointment or on-call roster; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

