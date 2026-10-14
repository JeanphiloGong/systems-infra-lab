# T03 v2 写作计划

前置v1。目标读取期间持有行锁，场景和模型见正文开头。任务1：从前版缺口建立输入和机制，规模M。任务2：解释调度/失败/资源边界，依赖任务1，规模M。任务3：完整row_lock.py checkpoint及真实运行（v4纯模型），依赖任务2，规模M。每步目标为同目录tutorial.md对应章节。测试检查具体返回与最终状态，完整代码从Markdown提取独立重放；不提交Git，独立review后验收。


## Tutorial Increment

- **Pressure:** The two workers decrementing shared inventory scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v1通过版本条件拒绝旧写入；高争用下调用者可能反复失败。现在让竞争者等待，等持锁者完成后再读取新值。模型只有一行库存，两个工作连接和一个只观察锁等待的连接。 关键变化是把SELECT quantity FOR UPDATE与UPDATE放在同一事务里。只锁SELECT然后立刻提交没有用。持锁者读10并持有锁，第二个连接的SELECT必须等它提交；在READ COMMITTED下醒来后读9，再减到8。
- **Change:** # T03 v2：读取期间持有行锁; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/locking -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T03 locking teaching model for two workers decrementing shared inventory; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of T03 locking, carrying forward the state and invariant rather than restarting from a disconnected example.

