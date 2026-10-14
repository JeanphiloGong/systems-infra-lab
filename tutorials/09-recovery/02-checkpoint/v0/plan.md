# A02 v0：量出完整日志恢复代价

## 场景与前版缺口

账户服务确认转账后重启，需要从 WAL 前缀重建余额。本版不设 snapshot，先建立完整 replay 的时间/字节基线。

## Pressure / Naive / Break

- **Pressure**：每次重启都必须恢复一致状态，同时实际读取量随历史增长。
- **Naive**：没有 checkpoint，恢复只能从第一个事务读取全部 WAL。
- **Break**：空目录恢复为 `({'alice':100,'bob':100}, 0, 0)`；写入 10 个事务后恢复为 `{'alice':90,'bob':110}`、position `10`，bytes_read 等于实际 WAL 文件大小；缺段、截断和 checksum 错误必须拒绝。

## Change

只冻结 framing、状态校验、完整 WAL replay 和 torn temporary file 忽略；不加入 snapshot。

## Check / Freeze

冻结 `labs/storage/wal/framing.py` 与 `labs/recovery/checkpoint/baseline.py`。v0 exact-fence probe 与 baseline tests 全部通过，恢复结果不得只回显输入规模。

## Still-lacks / Next

恢复成本随历史增长，没有 snapshot publication。v1 只加入 snapshot 加 tail replay，并用 bytes_read 证明只读尾部。

## Replay

```bash
uv run pytest tests/recovery/checkpoint/test_baseline.py -q
```
