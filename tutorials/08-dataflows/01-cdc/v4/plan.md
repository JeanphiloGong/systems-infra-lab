# E01 v4：暂停消费者保留 WAL

## 场景与前版缺口

承接 v3 的事务 checkpoint。消费者停止确认 slot，而源库继续写入大批事件；PostgreSQL 必须保留该 slot 仍需要的变更，恢复后才可推进。

## Pressure / Naive / Break

- **Pressure**：暂停消费超过 20,000 个事件，确认 retained WAL 增长；恢复后确认位置必须前进。
- **Naive**：忽略 slot lag 会误以为源端已可回收 WAL，最终让消费者无法追赶。
- **Break**：输出必须满足 `events_replayed > 20000`、`retained_bytes > 0`、`confirmed_advanced=true`，并在恢复后读取完整批次。

## Change

只加入暂停/恢复确认、批量事件生成和 slot retained bytes/position 观测；不加入吞吐优化或分布式消费者。

## Check / Freeze

冻结 `common.py` 与 `v4.py`。实验成功表示 slot 在暂停期保留事件、恢复后 confirmed position 前进；失败应清楚暴露 PostgreSQL 磁盘或配置不足。

## Still-lacks / Next

保留量取决于 PostgreSQL 配置、WAL 段和工作负载，不是容量或吞吐保证；跨进程协调和背压仍未覆盖。

## Replay

```bash
uv run pytest tests/dataflows/cdc/test_e01_replay.py -q
```

外部依赖：需要 PostgreSQL logical replication、足够 WAL 磁盘，以及 `E01_DATABASE_URL`。
