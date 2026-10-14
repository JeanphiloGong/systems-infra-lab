# A02 v2：先发布可验证 snapshot，再回收 WAL

## 场景与前版缺口

承接 v1 的 snapshot/tail。发布或目录同步过程中可能崩溃，旧 WAL 只能在新 snapshot 已验证并原子发布后回收。

## Pressure / Naive / Break

- **Pressure**：snapshot replace、directory fsync 和 reclaim 各有 crash boundary。
- **Naive**：先删 WAL 再验证 snapshot，会留下无法恢复的混合状态。
- **Break**：fault `before_replace`/`after_replace`/`after_directory_sync` 返回 71/72/73 后仍恢复 position 5；损坏 snapshot 的 publish 抛 `no usable recovery base` 且旧 WAL 仍存在。

## Change

只加入 snapshot 可恢复性验证、原子 manifest publication 和验证之后的 WAL reclaim；不加入多代 fallback。

## Check / Freeze

冻结 framing、baseline、store 三个围栏。`test_store.py` 的 crash boundary、invalid snapshot 和 `0 ({'alice':95,'bob':105},5)` replay probe 必须通过。

## Still-lacks / Next

只有一代 snapshot；最新基线损坏时没有旧代可回退。v3 只保留多代并在连续性验证后选择旧代恢复。

## Replay

```bash
uv run pytest tests/recovery/checkpoint/test_store.py -q
uv run python tests/recovery/checkpoint/replay_a02.py
```
