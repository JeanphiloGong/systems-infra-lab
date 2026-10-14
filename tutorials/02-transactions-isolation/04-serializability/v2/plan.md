# T04 v2 写作计划

前置v1真实SERIALIZABLE中止。目标完成被中止的医生请求，重新读取后拒绝最后一人离岗；两连接、两医生、一次屏障保留原冲突场景。

1. 解释v1只中止而未完成请求的缺口。目标tutorial.md第1节；规模S，无代码。
2. 新增retry_once与concurrent_retry，规模M，依赖1；解释异常在事务块外、max_retries预算及屏障只在首次进入。验收实际发生SerializationFailure后重新读取，输出一True、一False，重试至少1；不是干净状态的无竞争调用。
3. 完整serializable.py checkpoint和schema，规模M，依赖2；不包含未来measure_once或metrics参数。从Markdown提取到临时目录真实运行--retry并核对结果。事务超时和唯一schema清理沿用v1。

不提交Git。独立review重点：胜者退出后重试不能再等待屏障，拒绝业务决定不是数据库失败，预算耗尽必须传播。


## Tutorial Increment

- **Pressure:** The a constrained appointment or on-call roster scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v1让数据库中止不可串行历史，却没有完成被中止的业务请求。若直接重复旧的“可以下班”决定，仍可能让最后一人离开。本版重试的是完整事务：新快照、新人数、新判断。 两个医生初始都在岗。两个连接都在SERIALIZABLE事务中读取人数2，用Barrier(2)保证两次读取先完成，再各自更新。一个事务成功，另一个可能在UPDATE或COMMIT收到SerializationFailure；catch必须在with transaction之外，使两种失败都被捕获并完成回滚。
- **Change:** # T04 v2：失败的请求必须重新判断; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/serializable -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T04 serializability teaching model for a constrained appointment or on-call roster; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of T04 serializability, carrying forward the state and invariant rather than restarting from a disconnected example.

