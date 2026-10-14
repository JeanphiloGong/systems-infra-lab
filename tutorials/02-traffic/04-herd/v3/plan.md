# F04 v3：抖动过期与 stale-while-revalidate

## 场景与前版缺口

承接 v2 的进程内 single-flight。所有键同一时刻过期会形成峰值；热点值在刷新期间需要立即返回旧值，但超过 stale window 必须等待新值。

## Pressure / Naive / Break

- **Pressure**：抖动降低同步峰值；SWR 只能在 stale window 返回旧值；刷新失败不能延长旧值有效期。
- **Naive**：固定 TTL 同时过期；v2 没有 fresh/stale/hard-expiry 三态，也没有后台刷新。
- **Break**：同步和 jitter 波次都为 20 次调用但 jitter peak 更低且同 seed 可重放；20 个 stale 请求立即得到 `old` 且只有一次 fill；hard expiry 等待 `new`；失败后到硬过期必须传播错误；两个子进程输出 `[1, 1]`。

## Change

只加入逻辑 expiry jitter、fresh/stale/hard-expiry 状态和后台 refresh；不加入跨进程协调。

## Check / Freeze

冻结 `v0.py`、`v2.py`、`v3.py` 围栏。JSON 必须满足 `synchronized.peak > jittered.peak`、`swr_stale_responses=20`、`swr_fills=1`、`per_process_fills=[1,1]`；正文源码逐字匹配并在 15 秒内完成。

## Still-lacks / Next

进程内 flights 不会跨进程去重，逻辑 TTL 也不是墙钟延迟保证；分布式锁或共享缓存不在本版范围。

## Replay

```bash
uv run pytest tests/traffic/herd/test_f04.py -q -k '[3]'
```
