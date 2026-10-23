# E02：Schema Evolution

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

本专题在真实 PostgreSQL 上演示一个 `name` 到 `full_name` 的兼容迁移：先观察直接改名如何击穿旧客户端，再增加可选列并双写，接着用可暂停、可重复的批量回填补齐历史数据，最后在旧客户端退出后加约束并删除旧列。

运行前启动专用服务：

```bash
docker compose -f infra/e02.compose.yaml up -d --wait
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest tests/dataflows/schema_evolution -q
```

</details>

```bash
docker compose -f infra/e02.compose.yaml down -v
```
