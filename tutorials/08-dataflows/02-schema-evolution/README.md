# E02：Schema Evolution

本专题在真实 PostgreSQL 上演示一个 `name` 到 `full_name` 的兼容迁移：先观察直接改名如何击穿旧客户端，再增加可选列并双写，接着用可暂停、可重复的批量回填补齐历史数据，最后在旧客户端退出后加约束并删除旧列。

运行前启动专用服务：

```bash
docker compose -f infra/e02.compose.yaml up -d --wait
E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest tests/dataflows/schema_evolution -q
docker compose -f infra/e02.compose.yaml down -v
```
