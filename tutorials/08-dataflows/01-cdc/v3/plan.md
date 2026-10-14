# E01 v3：投影与消费位置同事务提交

## 场景与前版缺口

承接 v2 的快照与 tail。worker 可能在目标提交前、目标提交后但源确认前退出；恢复必须既不丢投影也不错误推进 source position。

## Pressure / Naive / Break

- **Pressure**：目标 SQLite 的 projection rows 和 checkpoint 必须同事务提交，源 slot 只能在成功提交后确认。
- **Naive**：分开写 projection/checkpoint 会产生“数据已写位置未写”或反向状态。
- **Break**：提交前崩溃后 projection 仍为初始 snapshot、checkpoint 为空；提交后崩溃后 checkpoint 恰有一条真实末尾 position；第三个 fresh worker 重放同一事件仍得到相同投影，`replay_safe=true`。

## Change

只加入单 SQLite 事务、`peek_changes` 上界读取、提交后 `get_changes` 确认和幂等 checkpoint key；不声称外部副作用 exactly-once。

## Check / Freeze

冻结 `common.py` 与 `v3.py`。输出必须包含 `checkpoints=1`、`version=7`、`fresh_processes=3`、`source_ack_after_commit=true` 以及两个 crash 标志为真。

## Still-lacks / Next

只有一个消费者和固定 orders schema；暂停消费者会无限保留 WAL。v4 只测暂停 slot 时的 retained WAL，恢复后观察确认位置前进。

## Replay

```bash
uv run pytest tests/dataflows/cdc/test_e01_replay.py -q
```

外部依赖：需要 PostgreSQL replication slot 和独立 worker subprocess。
