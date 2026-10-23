# P01：分区路由

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

从单分片订单字典出发，比较三种路由选择。只操作内存数据，不需要数据库。

- [v0：单分片读写](v0/tutorial.md)
- [v1：稳定哈希与取模](v1/tutorial.md)
- [v2：范围路由](v2/tutorial.md)
- [v3：一致性哈希与虚拟节点](v3/tutorial.md)

代码创建目标是 `labs/partitioning/routing/`，各策略是对照实验，不提供通用路由适配层。
可选执行 [参考分支检查](../../../docs/reference-checks.md) 检查当前代码；各版正文提供完整代码与独立验证命令。
审核状态以根目录的 [进度记录](../../../docs/progress.md) 为准。

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/partitioning/routing/
```

</details>
