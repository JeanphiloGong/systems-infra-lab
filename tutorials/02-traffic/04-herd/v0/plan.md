# F04 v0：同时过期造成回源风暴

## 场景与前版缺口

一个热点键在逻辑时间 5 过期，20 个协程读取同一缓存。当前没有协同机制；本版建立可测量并发基线。

## Pressure / Naive / Break

- **Pressure**：所有请求需要新值，但源站只能承受有限并发。
- **Naive**：每个 miss 直接 `origin.load`，没有 pending 记录。
- **Break**：20 个任务让出一次调度后，必须有 `origin.active == peak == calls == 20`；放行源站后 20 个结果都是 `new:hot`，活动数回到 0。

## Change / Check / Freeze

本版不修复，只冻结 `labs/traffic/herd/v0.py` 基线。JSON 报告 `requests=20`、`origin_calls=20`、`peak=20`；测试逐字提取正文源码并独立运行。

## Still-lacks / Next

Event 只测协程重叠，不代表网络吞吐；没有同键去重。v1 只加入每个 key 一个 pending fill task。

## Replay

```bash
uv run pytest tests/traffic/herd/test_f04.py -q -k '[0]'
```
