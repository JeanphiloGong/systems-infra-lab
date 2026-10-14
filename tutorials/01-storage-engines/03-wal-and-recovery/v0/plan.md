# S03 v0 写作计划

目标是亲眼观察直接覆盖无法保护两次更新的原子性，而非在本版解决问题。输入初始 JSON 为 alice=100、bob=100；正常转账结果 90/110，中间退出留下 90/100。

1. 建立转账调用者与总额不变量，展示扣款、入账是两个持久化动作。正文“写两次不等于一个事务”；验收读者能预测两个故障位置。无依赖，规模 S，代码角色说明。
2. 新建完整 baseline.py，子进程使用 os._exit(73) 在第一次覆盖完成后退出。正文“在确定边界退出”；验收退出码 73、磁盘 JSON 总额 190，正常分支 200。依赖任务 1，规模 S，完整 checkpoint。
3. 临时目录启动两个子进程，检查正常和故障路径。解释不是断电，也没声称覆盖文件本身原子。冻结可重复故障，下一版先构建日志记录边界。依赖任务 2，规模 S。

失败实验只退出自己创建的子进程；没有 fsync，不能把进程可见结果称为断电持久化。保留 baseline.py 是后续对照实验，不是兼容包装器。检查点提交：本轮不提交。


## Tutorial Increment

- **Pressure:** The a confirmed order write during a process crash scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 支付服务把 Alice 的 10 元转给 Bob。Alice 与 Bob 各有 100 元，成功后应为 90 和 110，总额仍为 200。先别讨论数据库，假设我们只把账户字典写进一个 JSON 文件。 我们将实际系统压缩为固定账户、固定金额和单个写者。输入文件由实验生成，不处理负余额、用户认证或并发请求。本篇故意实现不安全版本，让一个确定的退出位置揭示问题。它不是推荐的持久化实现。
- **Change:** # S03 v0：进程退出后，转账只完成了一半; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/wal -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S03 WAL/recovery teaching model for a confirmed order write during a process crash; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of S03 WAL/recovery, carrying forward the state and invariant rather than restarting from a disconnected example.

