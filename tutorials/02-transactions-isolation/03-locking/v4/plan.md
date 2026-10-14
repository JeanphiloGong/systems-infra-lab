# T03 v4 写作计划

前置v3。目标锁升级改变阻塞范围，场景和模型见正文开头。任务1：从前版缺口建立输入和机制，规模M。任务2：解释调度/失败/资源边界，依赖任务1，规模M。任务3：完整escalation.py checkpoint及真实运行（v4纯模型），依赖任务2，规模M。每步目标为同目录tutorial.md对应章节。测试检查具体返回与最终状态，完整代码从Markdown提取独立重放；不提交Git，独立review后验收。


## Tutorial Increment

- **Pressure:** The two workers decrementing shared inventory scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置v3。大量行锁需要大量锁记录；能否用一条表锁代表同一个事务的全部行锁？这就是本版要比较的机制。下面是独立的单线程教学模型，不连接PostgreSQL。PostgreSQL不会做SQL Server式的自动行锁升级。 模型只支持一张表的排他锁，不含意向锁、共享锁、等待队列、公平性或数据库完整死锁检测。acquire(owner,row)成功返回True，冲突返回False；它不阻塞线程。rows记录行到拥有者映射。同一拥有者重复获取允许成功。
- **Change:** # T03 v4：锁升级改变阻塞范围; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/locking -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T03 locking teaching model for two workers decrementing shared inventory; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

