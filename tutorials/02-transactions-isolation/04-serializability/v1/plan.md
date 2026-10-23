# T04 v1 计划

使用 Barrier 协调两个 `SERIALIZABLE` 事务同时读取；一方被 `SerializationFailure` 中止，另一方提交。测试只断言一个失败与最终至少一人值班，不固定胜者。完整入口包含 schema 初始化与清理。


前置：本模块 v0。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. 创建 serializable/schema.sql 与 serializable.py，让两个 SERIALIZABLE 事务先各自读取值班数，再由 Barrier 协调各自更新不同医生行。
2. 直接运行并断言恰好一次 SerializationFailure、最终至少一人值班；失败事务回滚。当前没有 retry_once/--retry，完整重读决策的重试在 v2 增加。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
