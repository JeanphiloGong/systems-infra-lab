# F04 v1：每个键一个 in-flight fill

## 场景与前版缺口

承接 v0 的 20 次同键回源。请求应共享同一个填充任务，但不同键不能错误共享结果。

## Pressure / Naive / Break

- **Pressure**：同键一次回源，不同键保持独立；完成后 pending 必须清理。
- **Naive**：v0 每个协程直接加载，峰值和源调用数都为 20。
- **Break**：在第一次 await 前注册 task；20 个 `hot` 请求必须 `same_key_calls=1`，`a`/`b` 恰好两次回源且分别返回 `new:a`、`new:b`。

## Change / Check / Freeze

只加入 `Flights.pending` 的按键任务复用和 identity-safe 清理，冻结 `v0.py`、`v1.py` 围栏。JSON 报告 `same_key_calls=1`、`distinct_key_calls=2`，并确认 pending 为空。

## Still-lacks / Next

直接 await 会让一个等待者取消共享 task；没有 waiter deadline 或 fill timeout。v2 只加入取消隔离、两类 timeout 和异常清理。

## Replay

```bash
uv run pytest tests/traffic/herd/test_f04.py -q -k '[1]'
```
