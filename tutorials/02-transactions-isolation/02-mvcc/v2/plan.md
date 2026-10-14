# T02 v2 计划

前置 v0/v1，回到真实 PG。两医生分别请求下班，每人看到人数>1才更新自己；模型两个重叠 RR 事务、不同写行。外部输出两次判定人数与最终人数，故意暴露 2/2/0，不把它当安全业务实现。

1. 第一步规模 S，checkpoint 顺序更新，第二次请求看到1而保留在岗；从调用者请求而非锁结构开始。
2. 第二步规模 M，patch 把两个查询提前到任一提交之前，再各改不同行；验收真实 2/2/0 与两行 false。明确第二事务先提交，第一事务后提交。
3. 最后一步规模 M，write_skew.py 完整 checkpoint，初始化 schema 沿用 v0，函数仅返回轨迹，无重试。独立重放并与顺序结果对比。下一版把共享不变量变成共享写冲突。所有任务不提交，review后冻结。


## Tutorial Increment

- **Pressure:** The two doctors deciding whether both can leave scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 医院要求至少一名医生在岗。两人初始都在岗，各自点击下班；程序先查询人数，大于 1 才允许自己离开。单独看每次请求似乎正确，但是两个请求可以使用不同事务同时判断。 本版回到 [v0](../v0/tutorial.md) 的真实 PostgreSQL；[v1](../v1/tutorial.md) 的列表模型只解释历史读取，不负责证明并发异常。两行分别为医生1和2，规则是跨行的 `count(on_call) >= 1`。
- **Change:** # T02 v2：两个正确快照，零个值班医生; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/mvcc -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T02 MVCC teaching model for two doctors deciding whether both can leave; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of T02 MVCC, carrying forward the state and invariant rather than restarting from a disconnected example.

