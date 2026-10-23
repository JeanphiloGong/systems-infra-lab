# T04 v3 写作计划

前置v2真实竞争及有界完整重试。目标记录十轮二连接竞争的吞吐、中止尝试、重试和业务决定，不承诺固定性能值。

1. 定义operations/committed/allowed/refused/aborted_attempts的计数口径，规模S，tutorial.md第1节。正常提交包含拒绝事务；异常耗尽则不返回完整报告。
2. 新增measure_once，规模M，依赖1；每轮重置两人在岗，调用concurrent_retry并累加，monotonic覆盖整个循环。解释线程和初始化开销。
3. 完整checkpoint加入--metrics入口，规模M，依赖2；从Markdown提取完整代码和schema独立运行。核对20操作/20提交、10允许/10拒绝、最终1在岗、重试至少10和正时间/吞吐。记录真实机器环境而非固定性能承诺。

不提交Git。独立review核对报告来自实际执行、v2没有提前携带metrics、严格可串行化定义包括非重叠操作实时顺序但本实验没有证明它。
