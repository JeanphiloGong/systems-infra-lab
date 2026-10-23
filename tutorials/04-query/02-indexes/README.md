# Q02：二级索引与覆盖读取

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

前置：[Q01 数据建模](../01-modeling/README.md)；内部机制可参考 [S02 B+Tree](../../01-storage-engines/02-b-plus-tree/README.md)。实验读取真实 PostgreSQL 执行计划。

- [v0：无索引扫描工作量](v0/tutorial.md)
- [v1：二级索引与选择性](v1/tutorial.md)
- [v2：复合索引列顺序、范围与排序](v2/tutorial.md)
- [v3：Index-Only Scan 与 heap 访问](v3/tutorial.md)
- [模块计划](plan.md)

先按[环境准备](../../../docs/environment.md)启动隔离数据库并配置 `SYSTEMS_LAB_DATABASE_URL`，再在仓库根目录运行：

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/query/indexes -q
uv run python tests/query/indexes/replay_q02.py
```

</details>

未配置数据库时部分测试会跳过，不能计作真实数据库验证。验收状态与审核证据见[实施进度](../../../docs/progress.md)。
