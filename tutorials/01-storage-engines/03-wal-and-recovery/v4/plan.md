# S03 v4 写作计划

前置 v3。目标是确认顺序严格晚于日志 flush/fsync，初始化同步目录项，修尾同步后追加。POSIX 本地单写者，父目录预先持久化，不声称实测断电。

1. 从 write 仅可能进入用户缓冲的具体失败解释 flush/fsync/目录项差异。正文“明确三个不同的完成点”；验收写→flush→fsync→返回的链条。依赖 v3，规模 S。
2. 添加 event 回调暴露动作完成点并同步日志，完整 checkpoint framing.py + store.py。验收精确轨迹、fsync 抛错不产生 before_ack、失败后可能恢复完整事务。依赖任务 1，规模 M。
3. 重放并明确回调探针不是持久化证明，冻结正确确认顺序，下一步真实退出矩阵。依赖任务 2，规模 S。

新 helper emit 只调用可选探针，无恢复策略；必要性来自可验证顺序与故障边界。data.json 非权威副本，不要求 fsync。提交策略：本轮不提交。


## Tutorial Increment

- **Pressure:** The a confirmed order write during a process crash scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v3](../v3/tutorial.md)。Python 的 write 成功，可能只写进用户态缓冲；flush 把缓冲交给 OS，仍可能只是 OS 页缓存。如果在此时告诉客户“成功”，断电可能让这个承诺无法兑现。 本篇限定本地 POSIX 文件系统、单写者、目录由调用者事先创建且其存在已持久化。我们按 fsync 合同安排顺序，不在普通进程实验里声称真的拔过电。文件系统、挂载选项、设备写缓存和硬件是否遵守持久化请求仍然影响真实保证。
- **Change:** # S03 v4：成功确认必须晚于日志同步; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/wal -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S03 WAL/recovery teaching model for a confirmed order write during a process crash; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v5 of S03 WAL/recovery, carrying forward the state and invariant rather than restarting from a disconnected example.

