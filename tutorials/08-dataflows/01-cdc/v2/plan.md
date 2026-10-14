# E01 v2：一致快照衔接增量 tail

## 场景与前版缺口

承接 v1 的 slot 事件流。一个新投影既要得到已有订单，又不能漏掉快照期间提交的变更。

## Pressure / Naive / Break

- **Pressure**：在逻辑 cut 上复制源表，记录 cursor，再只应用 cursor 之后的事件。
- **Naive**：先无界读取表再另读 slot，会重复或遗漏快照边界。
- **Break**：最终投影必须为 `{"1":"paid in full; customer's order","2":"after-snapshot","4":"new incarnation"}`，操作序列为 `UPDATE, DELETE, DELETE, INSERT, INSERT`，且 `0 < snapshot_cursor < last_source_position`。

## Change

只加入事务内 snapshot cut、cursor 记录和增量 tail 应用；拒绝不落后于最终事件位置的 cursor。

## Check / Freeze

冻结 `common.py` 与 `v2.py`。输出 `matches_source=true`，投影等于预期字典，cursor 数值严格早于最后 source position。

## Still-lacks / Next

快照、cursor 与投影尚未原子发布；worker 在两者之间崩溃仍可能重复或丢失。v3 只把投影行与 checkpoint 放进同一目标事务，并验证 crash boundary。

## Replay

```bash
uv run pytest tests/dataflows/cdc/test_e01_replay.py -q
```

外部依赖：需要专用 PostgreSQL 服务、logical slot 和可阻塞写入的事务。
