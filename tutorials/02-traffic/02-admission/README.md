# F02：负载均衡、限流与背压

前置：[F01 连接管理](../../01-storage-engines/07-connections/README.md)。本地线程与合成服务延迟用于观察排队、拒绝和调度行为，不代表生产网络吞吐。

- [v0：无限队列隐藏过载](v0/tutorial.md)
- [v1：限制在途工作](v1/tutorial.md)
- [v2：令牌桶速率与突发限制](v2/tutorial.md)
- [v3：Worker 选择策略](v3/tutorial.md)
- [v4：慢服务与背压传播](v4/tutorial.md)
- [模块计划](plan.md)

在仓库根目录运行：

```bash
uv run pytest tests/traffic/admission -q
uv run python tests/traffic/admission/replay_f02.py
```

验收状态与审核证据见[实施进度](../../../docs/progress.md)。
