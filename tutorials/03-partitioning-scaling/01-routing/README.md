# P01：分区路由

从单分片订单字典出发，比较三种路由选择。只操作内存数据，不需要数据库。

- [v0：单分片读写](v0/tutorial.md)
- [v1：稳定哈希与取模](v1/tutorial.md)
- [v2：范围路由](v2/tutorial.md)
- [v3：一致性哈希与虚拟节点](v3/tutorial.md)

代码位于 `labs/partitioning/routing/`，各策略是对照实验，不提供通用路由适配层。
运行 `uv run pytest tests/partitioning/routing/` 检查当前代码；各版正文提供完整代码与独立验证命令。
审核状态以根目录的 [进度记录](../../../docs/progress.md) 为准。
