# Q04 物化视图与缓存

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

[v0 现场聚合](v0/tutorial.md)、[v1 物化旧读](v1/tutorial.md)、[v2 刷新与锁](v2/tutorial.md)、[v3 TTL](v3/tutorial.md)、[v4 失效竞态](v4/tutorial.md)。

使用独立 PostgreSQL 服务，先设置 `SYSTEMS_LAB_DATABASE_URL`：

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/query/derived -q
uv run python tests/query/derived/replay_q04.py
```

</details>
