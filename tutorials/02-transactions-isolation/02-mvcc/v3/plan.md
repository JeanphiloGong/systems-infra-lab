# T02 v3 计划

前置 v2，仍用真实 RR。目标让两人同时下班的调度留下至少1人；采用单排班组 guard 行更新作为共享冲突点，冲突事务必须回滚后重做整个读取/决策。不是切换 Serializable，也不是通用锁服务。

1. tutorial.md 第一步，规模 S，guard.sql checkpoint，解释不同行缺乏共同写冲突，新增唯一 guard 行，不改变医生 schema。
2. 第二步规模 M，protected_schedule 初始冲突片段 checkpoint；旧快照 second 先建立，first 更新 guard+下班提交，second 更新 guard 得40001。验收冲突明确抛出，不是依赖线程等待。
3. 第三步规模 M，patch 新事务完整重读并判定；返回 conflict1/allowed false/remaining1。仅本确定性实验重试一次，无泛化重试承诺。
4. 最后完整 protected.py checkpoint，依赖前三步，规模 M。真实 SQL 加最终行状态测试，独立正文重放。解释所有写者必须遵守协议、争用成本、重试责任，不断言任意跨行约束自动安全。无提交。


## Tutorial Increment

- **Pressure:** The two doctors deciding whether both can leave scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** [v2](../v2/tutorial.md) 中两个医生各写自己一行，所以 RR 没有检测到写写冲突。现在保持相同隔离级别，要求所有修改本排班组的人先更新同一条 guard 记录。这样旧快照继续执行时，冲突就落到数据库能检测的一行上。 这个策略只保护遵守协议的写者。绕过 guard 的直接 UPDATE 仍能破坏规则。模型只有一个排班组；生产系统可以按组拆分 guard，但本课不引入租约、分布式锁或自动重试框架。
- **Change:** # T02 v3：把共同规则变成共同冲突点; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/mvcc -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T02 MVCC teaching model for two doctors deciding whether both can leave; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

