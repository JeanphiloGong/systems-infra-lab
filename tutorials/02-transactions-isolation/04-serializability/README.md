# T04：可串行化与事务重试

前置 T02/T03。使用真实 PostgreSQL `SERIALIZABLE` 保护值班约束，比较并发历史与确定性串行参考。按 v0-v3 顺序阅读；代码在 `labs/transactions/serializable/`，测试在 `tests/transactions/serializable/`。
