# F03 v1：错误分类与总截止时间

## 场景与前版缺口

承接 v0 的立即重试。服务会返回可恢复的 `RetryableError` 和不应重试的 `PermanentError`；v0 把两者都重试，也没有总时间边界。

## Pressure / Naive / Break

- **Pressure**：验证错误必须立即停止；持续可重试错误必须在 `deadline` 到达时停止。
- **Naive**：v0 对所有 `Exception` 重试，可能重复无效写入。
- **Break**：`PermanentError` 操作只调用一次并原样抛出；时钟序列 `[0.0, 0.0, 1.1]` 的可重试操作抛出 `TimeoutError`。

## Change

只加入两类异常、`max_attempts`/deadline 校验和一次请求共享的 deadline；不加入 sleep、随机数或熔断。

## Check / Freeze

冻结 `labs/traffic/resilience/v1.py`。成功返回 `('ok', 1)`；永久错误不重试；连续可重试错误在 deadline 前耗尽时为 `TimeoutError`；非法 attempts 或负 deadline 为 `ValueError`。

## Still-lacks / Next

本版未测量真实操作耗时，也没有退避和 jitter。v2 只加入指数退避、jitter 和实际 I/O 截止示例。

## Replay

```bash
uv run pytest tests/traffic/retry/test_replay_f03.py -q
```
