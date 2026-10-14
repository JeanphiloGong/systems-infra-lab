# Q01：规范化与反规范化

前置：[T01 事务隔离](../../02-transactions-isolation/01-isolation/README.md)。通过订单与客户模型观察更新异常、读模型维护和历史快照边界。

- [v0：重复客户数据发生漂移](v0/tutorial.md)
- [v1：规范化与读取时关联](v1/tutorial.md)
- [v2：维护反规范化读模型](v2/tutorial.md)
- [v3：读写成本与历史快照](v3/tutorial.md)
- [模块计划](plan.md)

在仓库根目录运行：

```bash
uv run pytest tests/query/modeling -q
uv run python tests/query/modeling/replay_q01.py
```

验收状态与审核证据见[实施进度](../../../docs/progress.md)。
