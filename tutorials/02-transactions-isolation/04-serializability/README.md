# T04：可串行化与事务重试

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

前置 T02/T03。使用真实 PostgreSQL `SERIALIZABLE` 保护值班约束，比较并发历史与确定性串行参考。按 v0-v3 顺序阅读；代码创建目标是 `labs/transactions/serializable/`，参考参考测试位于 `tests/transactions/serializable/`。
