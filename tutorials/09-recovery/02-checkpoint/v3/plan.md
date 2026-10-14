# A02 v3：多代 checkpoint 与 fallback

## 场景与前版缺口

承接 v2 的单代安全发布。最新 snapshot 可能损坏，所需 WAL 也可能缺失，generation rotation 还可能在 exit codes 71-75 处崩溃；恢复需要选择仍连续的旧代。

## Pressure / Naive / Break

- **Pressure**：验证每代 snapshot/WAL 连续性，再从最新可用代恢复。
- **Naive**：v2 只有一个基线，损坏后无法恢复；忽略缺段会产生静默错误状态。
- **Break**：损坏最新代时 fallback 经过 15 个 WAL 事务到 position 25；缺少 required segment 明确报错；rotation crash codes `[71,72,73,74,75]` 后保留旧有效代并继续到 position 31。

## Change

只加入两代独立 snapshot、连续性校验和从新到旧的 fallback；不加入 replicated checkpoint store 或跨主机恢复。

## Check / Freeze

冻结 framing、baseline、store 围栏。generation experiment 必须精确返回 `fallback_transactions=15`、`rotation_exits=[71,72,73,74,75]`、`continued_position=31`；缺段和损坏均拒绝。

## Still-lacks / Next

仍是本地文件系统 checkpoint，没有复制、备份或跨主机故障恢复。后续专题处理 backup 与 point-in-time restore。

## Replay

```bash
uv run pytest tests/recovery/checkpoint/test_store.py -q
uv run python tests/recovery/checkpoint/replay_a02.py
```
