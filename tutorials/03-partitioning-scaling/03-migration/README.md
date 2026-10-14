# P03：在线迁移与重分片

前置：[P01 分区路由](../01-routing/README.md)、[D01 幂等](../../07-coordination/01-idempotency/README.md)。实验使用本地分片模型研究迁移，不代表生产在线迁移性能。

- [v0：暂停写入后复制](v0/tutorial.md)
- [v1：后台复制的增量缺口](v1/tutorial.md)
- [v2：顺序增量日志重放](v2/tutorial.md)
- [v3：屏障、切换与过期路由](v3/tutorial.md)
- [v4：恢复与 fencing](v4/tutorial.md)
- [模块计划](plan.md)

在仓库根目录运行：

```bash
uv run pytest tests/partitioning/migration -q
uv run python tests/partitioning/migration/replay_p03.py
```

验收状态与审核证据见[实施进度](../../../docs/progress.md)。
