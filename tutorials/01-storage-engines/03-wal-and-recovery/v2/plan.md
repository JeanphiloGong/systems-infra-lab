# S03 v2 写作计划

前置 v1。目标是记录赋值意图并识别全部未提交事务，不越级声称可恢复已提交状态。两个账户初始均 100，单次日志用新路径。

1. 用重复“扣10”展示恢复非幂等，选择最终值赋值。再用只留下 Alice 帧展示候选 90/100，说明没有提交标记不可发布。正文“记录结果赋值”；验收两次 inspect 相同，单帧仍 pending。依赖 v1，规模 S。
2. 完整 checkpoint framing.py + prepared.py，prepare 先日志后可选数据；inspect_pending 只返回候选/未提交编号。验收 apply=False 数据未变、apply=True 仍 pending、日志字段非法拒绝。依赖任务 1，规模 M。
3. 重放独立临时目录检查，冻结意图日志版本并留下提交歧义。依赖任务 2，规模 S。

apply 分支只是可观察的程序阶段，不是崩溃模拟；本篇不承诺 fsync 持久化。helper 无兼容包装用途，prepared 留作与后续提交恢复的对照。提交策略：本轮不提交。


## Tutorial Increment

- **Pressure:** The a confirmed order write during a process crash scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v1](../v1/tutorial.md)。v0 只留下被覆盖的数据，没有可追踪意图。现在我们先把“将 Alice 设为 90，将 Bob 设为 110”写到追加日志，再改变数据文件。即使数据写入没有发生，也能从日志重建候选结果。 但存在一个关键问题：日志里的操作究竟是已经提交的交易，还是写到一半被放弃的尝试？本篇故意保留这个缺口，不把“能够重放”宣传为“已经支持事务恢复”。
- **Change:** # S03 v2：先记操作，仍不能把它叫作提交; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/wal -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S03 WAL/recovery teaching model for a confirmed order write during a process crash; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of S03 WAL/recovery, carrying forward the state and invariant rather than restarting from a disconnected example.

