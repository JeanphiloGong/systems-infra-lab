# F03 v0：立即重试的放大效应

## 场景与前版缺口

入口调用一个暂时失败的依赖。本版建立最小基线，展示“每次异常都立刻重试”如何把一次入口调用变成多次下游调用。核心不变量是调用次数可观测，达到上限后原始失败不能被伪装成成功。

## Pressure / Naive / Break

- **Pressure**：依赖连续失败时，调用方希望有限次数恢复，但下游需要知道真实尝试数。
- **Naive**：直接调用一次只得到失败，无法观察重试放大。
- **Break**：以 `max_attempts=3` 注入前两次异常；检查返回尝试次数为 `3`。所有异常都走同一分支，永久错误也会重试。

## Change

只加入固定次数的立即重试循环：`call(operation, max_attempts)` 每次失败立即再次调用，最后一次失败原样抛出。

## Check / Freeze

冻结 `labs/traffic/resilience/v0.py`。脚本输出 `('ok', 1)`；独立提取源码后补充计数器，三次失败后成功必须得到 `('ok', 3)`，永久失败以原异常退出。

## Still-lacks / Next

没有错误分类、总截止时间、退避、抖动、熔断或跨层预算。v1 只加入可重试/永久错误分类和一个总 deadline。

## Replay

```bash
uv run pytest tests/traffic/retry/test_replay_f03.py -q
```
