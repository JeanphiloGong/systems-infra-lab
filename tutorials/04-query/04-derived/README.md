# Q04 物化视图与缓存

[v0 现场聚合](v0/tutorial.md)、[v1 物化旧读](v1/tutorial.md)、[v2 刷新与锁](v2/tutorial.md)、[v3 TTL](v3/tutorial.md)、[v4 失效竞态](v4/tutorial.md)。

使用独立 PostgreSQL 服务，先设置 `SYSTEMS_LAB_DATABASE_URL`：

```bash
uv run pytest tests/query/derived -q
uv run python tests/query/derived/replay_q04.py
```
