# F03 v4：跨层共享重试预算

## 场景与前版缺口

承接 v3，但三层各自 `3` 次重试仍会产生 `3^3 = 27` 次叶子调用。入口需要一个共享预算，同时保持成功、永久错误和 deadline 的终止语义。

## Pressure / Naive / Break

- **Pressure**：限制真实下游叶子执行次数，而不是某层的进入次数。
- **Naive**：独立层级各自重试，三层失败执行 27 次叶子操作。
- **Break**：`amplification(None) == 27`、`amplification(10) == 10`；负层数为 `ValueError`；预算耗尽、永久错误和 deadline 保留精确调用计数。

## Change

只加入请求作用域 `Budget`，由最外层计算一个 deadline，所有层在执行叶子前消耗同一预算；不加入线程安全配额或跨进程共享。

## Check / Freeze

冻结 `labs/traffic/resilience/budget.py`。正文与回归检查通过，输出证明 `executed 27 vs 10`，并覆盖成功、预算耗尽、永久失败和 deadline。

## Still-lacks / Next

预算不限制中间函数进入次数，不能替代熔断、限流或背压；同步操作仍不可强制抢占。这是 F03 当前教学终点。

## Replay

```bash
uv run pytest tests/traffic/retry -q
```
