# E01 v1：读取已提交的 WAL 变更

## 场景与前版缺口

承接 v0 的源库/投影分歧。现在 worker 需要从 PostgreSQL logical replication slot 读取提交后的事件，保留事务顺序和可恢复的位置。

## Pressure / Naive / Break

- **Pressure**：INSERT、UPDATE、DELETE 必须按 source position 顺序产生唯一事件身份。
- **Naive**：v0 没有源端日志；按字符串排序 `pg_lsn` 也会破坏位置顺序。
- **Break**：slot 输出 BEGIN、三条数据变更和 COMMIT；必须有 `data_event_count=3`、唯一 data positions、`versions=[1..N]`，操作顺序为 `INSERT, UPDATE, DELETE`。

## Change

只加入 `test_decoding` slot 读取、结构化事件解析、真实 LSN 与 event key；不建立 snapshot 或目标投影事务。

## Check / Freeze

冻结 `common.py` 与 `v1.py` 围栏。JSON 中 source positions 数值单调、xid 为正、event keys 由 `xid:position:operation` 构成，且所有事务边界被保留。

## Still-lacks / Next

slot 是源流，不是 durable projection 或 snapshot bridge；尚未解决从既有数据开始消费。v2 只加入一致快照 cut 与其后的增量 tail。

## Replay

```bash
uv run pytest tests/dataflows/cdc/test_e01_replay.py -q
```

外部依赖：需要 PostgreSQL logical replication 和 `test_decoding`。
