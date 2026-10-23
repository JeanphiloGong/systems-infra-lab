# T02：MVCC 与 Snapshot Isolation

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

前置 [T01](../01-isolation/README.md)。通过两个值班医生学习快照、行版本和 Write Skew。
顺序为 [v0](v0/tutorial.md) → [v1](v1/tutorial.md) → [v2](v2/tutorial.md) → [v3](v3/tutorial.md)。

真实实验使用仓库 [环境](../../../docs/environment.md) 和 `SYSTEMS_LAB_DATABASE_URL`；所有命令在仓库根目录运行。
代码为 `labs/transactions/mvcc/`，测试为 `tests/transactions/mvcc/`。v1 单独标为教学模型，不能用它代替 PostgreSQL 行为证据。

完成后能够解释快照隔离为什么不等于串行化，并指出跨行规则的冲突点与重试责任。MVCC 的空间回收在 S07 继续学习。
