# T04 v2 写作计划

前置v1真实SERIALIZABLE中止。目标完成被中止的医生请求，重新读取后拒绝最后一人离岗；两连接、两医生、一次屏障保留原冲突场景。

1. 解释v1只中止而未完成请求的缺口。目标tutorial.md第1节；规模S，无代码。
2. 新增retry_once与concurrent_retry，规模M，依赖1；解释异常在事务块外、max_retries预算及屏障只在首次进入。验收实际发生SerializationFailure后重新读取，输出一True、一False，重试至少1；不是干净状态的无竞争调用。
3. 完整serializable.py checkpoint和schema，规模M，依赖2；不包含未来measure_once或metrics参数。从Markdown提取到临时目录真实运行--retry并核对结果。事务超时和唯一schema清理沿用v1。

不提交Git。独立review重点：胜者退出后重试不能再等待屏障，拒绝业务决定不是数据库失败，预算耗尽必须传播。
