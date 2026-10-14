# A02 v1：snapshot 加 WAL tail

## 场景与前版缺口

承接 v0 的完整 replay。100 个事务后发布 position 100 的 durable CRC snapshot，再追加 5 个事务；重启只应读取这 5 个 tail 文件。

## Pressure / Naive / Break

- **Pressure**：缩短恢复读取量，同时保持 snapshot 与 WAL 的 position 连续。
- **Naive**：v0 每次仍读取全部 105 个事务；不校验 snapshot 会把损坏状态当作基线。
- **Break**：100+5 事务测试的 `Store.recover()` 恢复为 `{'alice':96,'bob':104}`、position `105`，bytes_read 只等于 101-105 五个 WAL 文件；独立围栏 probe 使用 10+5 事务，结果为 `({'alice':85,'bob':115},15)`。

## Change

只加入 CRC framed snapshot、manifest、snapshot position 和 tail replay；所有 WAL 仍保留，不提前 reclaim。

## Check / Freeze

冻结 framing、baseline 和 `labs/recovery/checkpoint/store.py` 围栏。`test_store.py` 必须证明 recovered state 正确且 bytes_read 小于全部 WAL。

## Still-lacks / Next

snapshot 可能发布不完整，过早回收日志会使恢复无基线。v2 只加入发布前验证和发布后 reclaim 的 crash-safe 顺序。

## Replay

```bash
uv run pytest tests/recovery/checkpoint/test_store.py -q
uv run python tests/recovery/checkpoint/replay_a02.py
```
