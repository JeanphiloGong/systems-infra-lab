# F03 v2：截止时间内的退避与抖动

## 场景与前版缺口

承接 v1 的错误分类和 deadline。多个客户端同时重试会形成同步波峰；立即重试也没有为恢复留下时间。本版把等待纳入同一预算，并展示停滞 socket 必须由真实 I/O 超时解决。

## Pressure / Naive / Break

- **Pressure**：三次失败的退避应消耗实际等待；相同 seed 的 jitter 可重放，不同请求的到达应分散。
- **Naive**：v1 没有 delay/jitter，不能限制阻塞在 socket 上的同步操作。
- **Break**：真实默认 sleep 至少 `0.03s`；seed 后 jitter 序列相同，八个 arrival 落在断言窗口；停滞 socket 只尝试一次并超时。

## Change

只加入指数 delay `0.01, 0.02, ...`、可注入 sleep、随机 jitter 和 deadline 审查；`io_deadline.py` 单独用 socket timeout 演示同步 I/O 边界。

## Check / Freeze

冻结 `labs/traffic/resilience/v2.py` 与 `labs/traffic/resilience/io_deadline.py`。超调抛 `TimeoutError`；I/O JSON 满足 `attempts == 1`、`timed_out == true`、`thread_stopped == true`，且 `0.8 * budget_seconds <= elapsed_seconds < 1.0`。

## Still-lacks / Next

同步 Python 无法强制抢占任意函数，超时不撤销已发生的副作用；没有失败依赖的快速拒绝。v3 只加入进程内 circuit breaker。

## Replay

```bash
uv run pytest tests/traffic/retry/test_replay_f03.py tests/traffic/retry/test_io_deadline_replay.py -q
```
