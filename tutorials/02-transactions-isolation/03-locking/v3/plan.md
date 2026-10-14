# T03 v3 写作计划

前置v2。目标相反锁顺序形成等待环，场景和模型见正文开头。任务1：从前版缺口建立输入和机制，规模M。任务2：解释调度/失败/资源边界，依赖任务1，规模M。任务3：完整deadlock.py checkpoint及真实运行（v4纯模型），依赖任务2，规模M。每步目标为同目录tutorial.md对应章节。测试检查具体返回与最终状态，完整代码从Markdown提取独立重放；不提交Git，独立review后验收。


## Tutorial Increment

- **Pressure:** The two workers decrementing shared inventory scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置v2。一个订单要同时扣两个商品，另一个订单恰好反向访问；只拥有行锁不代表不会死锁。保持v1的schema.sql，在入口初始化后增加INSERT INTO inventory VALUES (2,10,0)，这是第二资源首次出现。 两个线程分别先锁1和2，在Barrier(2)会合后才请求另一行。此时各自持有对方需要的锁，PostgreSQL检测等待环并以DeadlockDetected（40P01）中止一个事务。受害者不固定，所以测试只断言恰好一个失败，不断言哪个线程失败。Barrier有超时；不使用slee
- **Change:** # T03 v3：相反锁顺序形成等待环; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/locking -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T03 locking teaching model for two workers decrementing shared inventory; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v4 of T03 locking, carrying forward the state and invariant rather than restarting from a disconnected example.

