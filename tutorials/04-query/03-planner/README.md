# Q03：查询计划与成本估计

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

前置：[Q02 索引](../02-indexes/README.md)、[P02 数据倾斜](../../03-partitioning-scaling/02-skew/README.md)。区分 PostgreSQL 估计值、实际行数与资源观测。

- [v0：数据增长与访问路径变化](v0/tutorial.md)
- [v1：陈旧统计信息与新热点](v1/tutorial.md)
- [v2：相关性与选择性估计](v2/tutorial.md)
- [v3：Join 工作量与排序溢出](v3/tutorial.md)
- [模块计划](plan.md)

先按[环境准备](../../../docs/environment.md)启动隔离数据库并配置 `SYSTEMS_LAB_DATABASE_URL`，再在仓库根目录运行：

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/query/planner -q
uv run python tests/query/planner/replay_q03.py
```

</details>

未配置数据库时部分测试会跳过，不能计作真实数据库验证。验收状态与审核证据见[实施进度](../../../docs/progress.md)。
