# Q03：查询计划与成本估计

前置：[Q02 索引](../02-indexes/README.md)、[P02 数据倾斜](../../03-partitioning-scaling/02-skew/README.md)。区分 PostgreSQL 估计值、实际行数与资源观测。

- [v0：数据增长与访问路径变化](v0/tutorial.md)
- [v1：陈旧统计信息与新热点](v1/tutorial.md)
- [v2：相关性与选择性估计](v2/tutorial.md)
- [v3：Join 工作量与排序溢出](v3/tutorial.md)
- [模块计划](plan.md)

先按[环境准备](../../../docs/environment.md)启动隔离数据库并配置 `SYSTEMS_LAB_DATABASE_URL`，再在仓库根目录运行：

```bash
uv run pytest tests/query/planner -q
uv run python tests/query/planner/replay_q03.py
```

未配置数据库时部分测试会跳过，不能计作真实数据库验证。验收状态与审核证据见[实施进度](../../../docs/progress.md)。
