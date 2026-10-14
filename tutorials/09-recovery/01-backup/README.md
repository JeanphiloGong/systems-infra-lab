# A01：Backup 与 PITR 边界

本专题使用独立 PostgreSQL 实例验证逻辑 dump、物理 base backup、损坏检测和目标时间恢复。v0-v2 使用真实 `pg_dump`/`pg_restore`；v3 使用 `pg_basebackup`、WAL 归档及第二个恢复容器到达误删前的时间；v4 在私有归档副本中删除必要 WAL，验证目标无法到达。恢复成功要求目标暂停状态和准确的数据结果。

```bash
docker compose -f infra/e03.compose.yaml up -d --wait
A01_DATABASE_URL='postgresql://a01:a01_local_only@127.0.0.1:55452/a01' uv run pytest tests/recovery/backup -q
docker compose -f infra/e03.compose.yaml down -v
```
