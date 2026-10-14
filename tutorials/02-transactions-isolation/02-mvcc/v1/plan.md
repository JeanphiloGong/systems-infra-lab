# T02 v1 计划

前置 v0 两条 PG 轨迹。目标解释旧状态保留；模型只有单键已提交版本列表、严格递增逻辑时间和快照界限。外部契约输入按时间递增列表与整数快照，输出最新可见布尔值，无可见版本抛 LookupError。无未提交、事务 ID、并发写、GC、锁，因此不是 PG 算法。

1. tutorial.md 起点，规模 S，checkpoint：覆盖单个 bool 后旧快照只能读 false；assert 展示无法还原 true。依赖 v0。
2. 第二步规模 S，patch：改成 [(1,true),(2,false)]，反向查找不晚于快照的版本；验收 snapshot1 true/snapshot2 false/创建前无值。版本由已知脚本生成，不新增通用事务管理器。
3. 最后一步规模 S，完整 model.py checkpoint，运行纯模型测试与真实 v0 实验，对齐观察但明确实现不可互换。冻结后下一版研究跨行不变量。所有任务不提交，独立审查。


## Tutorial Increment

- **Pressure:** The two doctors deciding whether both can leave scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** [v0](../v0/tutorial.md) 中，写者提交 false 后，旧读者仍读到 true。现在用一个十几行的教学模型解释这种能力。这个模型不是 PostgreSQL 源码，也不参与真实数据库测试；它只保存单个医生的已提交历史。 下面是可直接运行的 Python checkpoint：
- **Change:** # T02 v1：只保存当前值，无法回答旧快照; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/mvcc -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T02 MVCC teaching model for two doctors deciding whether both can leave; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of T02 MVCC, carrying forward the state and invariant rather than restarting from a disconnected example.

