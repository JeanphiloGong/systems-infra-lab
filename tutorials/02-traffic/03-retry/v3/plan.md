# F03 v3：熔断器的受控恢复

## 场景与前版缺口

承接 v2。依赖持续失败时，每个请求仍会把重试流量打到坏依赖；需要共享进程内健康状态，停止新调用并允许一次恢复探针。

## Pressure / Naive / Break

- **Pressure**：达到失败阈值后拒绝调用；恢复窗口只允许一个 half-open probe。
- **Naive**：v2 的策略按请求独立，无法共享依赖健康状态。
- **Break**：`CircuitBreaker(2)` 两次 failure 后为 `OPEN` 且 `allow()` 为假；recover 后第一次允许、第二次拒绝；success 后回到 `CLOSED`。

## Change

只加入 `CLOSED`、`OPEN`、`HALF_OPEN` 状态和受控探针；不加入分布式共享状态或全局预算。

## Check / Freeze

冻结 `labs/traffic/resilience/breaker.py`。独立执行和 probe 回归检查通过，探针成功后状态精确为 `State.CLOSED`。

## Still-lacks / Next

状态只在单进程内存在，嵌套调用仍可能乘法放大，也没有速率限制或背压。v4 只加入一次请求作用域的共享叶子预算。

## Replay

```bash
uv run pytest tests/traffic/retry/test_replay_f03.py tests/traffic/retry/test_breaker_budget.py -q
```
