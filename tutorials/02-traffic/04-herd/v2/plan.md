# F04 v2：隔离等待者取消并限制填充时间

## 场景与前版缺口

承接 v1 的共享 task。一个用户取消或等待超时不应取消仍在服务其他用户的 fill；源站失败、fill 超时和直接取消都必须清理 pending。

## Pressure / Naive / Break

- **Pressure**：区分 waiter timeout 与 origin fill timeout，并把同一失败扇出给所有等待者。
- **Naive**：v1 直接 await 共享 task，单个 waiter 的取消会传播给所有人。
- **Break**：取消 owner、超时 waiter 后 peer 仍完成且源只调用一次；失败扇出和 fill timeout 各只调用一次；取消 fill 后 pending 为空，后续请求能再次成功。

## Change

只加入 `asyncio.shield`、每 waiter 的 `asyncio.timeout`、fill 内部 timeout，以及 done callback 的 identity 清理和异常观察。

## Check / Freeze

冻结 `v0.py`、`v2.py` 围栏。JSON 必须满足 `cancelled_waiter_isolated`、`timed_out_waiter_isolated` 为真，`failure_fanout == fill_timeout_calls == 1`，取消 fill 后重试调用数为 2；不得出现 `Task was destroyed`。

## Still-lacks / Next

仍是单 event loop、单进程；不同进程的 pending 不共享。v3 只加入抖动过期、SWR 和硬过期语义，并显式展示进程边界。

## Replay

```bash
uv run pytest tests/traffic/herd/test_f04.py -q -k '[2]'
```
