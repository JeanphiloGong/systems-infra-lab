# D02：分布式锁与 Fencing

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

前置：[D01 幂等](../01-idempotency/README.md)、[C01 CAP/Quorum](../../06-consensus/01-cap-quorum/README.md)。本地锁与时钟模型用于观察租约重叠和资源端拒绝，不代表生产锁服务。

- [v0：原子获取只有一个赢家](v0/tutorial.md)
- [v1：租约过期与拥有者重叠](v1/tutorial.md)
- [v2：资源端 fencing](v2/tutorial.md)
- [v3：续租、释放与所有权](v3/tutorial.md)
- [v4：明确处理锁服务故障](v4/tutorial.md)
- [模块计划](plan.md)

在仓库根目录运行：

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/coordination/locks -q
uv run python tests/coordination/locks/replay_d02.py
```

</details>

验收状态与审核证据见[实施进度](../../../docs/progress.md)。
