# S03 v3 写作计划

前置 v2。模型：完整保留的 redo 日志、pending 事务、commit 标记、可丢弃数据副本。目标是只应用已提交组，重复恢复逻辑结果不变。

1. 用完整两条操作仍无法确认提交的案例推导 commit，规定事务号不复用，恢复从 INITIAL 而非不可信数据副本开始。正文“从初始状态重建”；验收未提交忽略、已提交全部应用。依赖 v2，规模 S。
2. 用半帧后直接追加导致新帧失去边界的问题推导只修整未完成尾，完整损坏报错。完整 checkpoint framing.py + store.py；验收半尾后新提交可恢复、重复编号拒绝、非法操作不修改日志。依赖任务 1，规模 M。
3. 重放正文并检查数据副本损坏仍恢复正确；冻结提交语义，留下无 fsync 的持久化缺口。依赖任务 2，规模 S。

replay 是恢复和写前验证的共同业务规则，返回状态与所有已用编号；Store 是路径与提交入口，不是兼容层。未提交完整帧保留并占用编号。提交策略：本轮不提交。


## Tutorial Increment

- **Pressure:** The a confirmed order write during a process crash scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v2](../v2/tutorial.md)。日志里只有 Alice=90 时不能发布余额；两条操作都有也仍然不能确定交易已提交。我们需要一条独立的 commit 记录，把“写了哪些操作”和“决定提交”分开。 本篇的事务是一组账户最终值赋值。提交记录前，所有操作只是 pending；看到对应 commit 后才一次更新恢复状态。不变量是一次事务的操作全部可见或全部不可见。金额是否守恒属于转账业务规则，本存储接口允许单账户赋值，事务原子性不自动验证转账业务。
- **Change:** # S03 v3：让提交标记决定哪些操作可见; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/wal -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S03 WAL/recovery teaching model for a confirmed order write during a process crash; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v4 of S03 WAL/recovery, carrying forward the state and invariant rather than restarting from a disconnected example.

