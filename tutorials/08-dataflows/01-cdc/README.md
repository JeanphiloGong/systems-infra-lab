# E01：CDC 与投影同步

E01 使用 E01 自己的 PostgreSQL 16 logical decoding 服务（55450），不连接共享数据库或 R04 服务。

```bash
docker compose -f infra/e01.compose.yaml up -d
export E01_DATABASE_URL='postgresql://e01:e01_local_only@127.0.0.1:55450/e01'
uv sync
E01_DATABASE_URL="$E01_DATABASE_URL" uv run python -m pytest tests/dataflows/cdc -q
docker compose -f infra/e01.compose.yaml down -v
```

- v0 双写失败造成不一致。
- v1 从 test_decoding slot 读取已提交增删改和 LSN。
- v2 slot-first 快照与增量去重。
- v3 投影和消费 checkpoint 同事务重放。
- v4 暂停 slot、批量写入、观察 WAL 保留与恢复确认位置。

这是 PostgreSQL 16 固定版本和 test_decoding 的教学实验。传输不是全局有序，WAL 字节差不是总磁盘使用量，外部投影仍需自己的幂等边界。清理只使用本 compose 项目 down -v。
