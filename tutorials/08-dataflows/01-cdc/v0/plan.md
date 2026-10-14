# E01 v0：源库与投影发生分歧

## 场景与前版缺口

订单写入 PostgreSQL 源库后，投影 worker 尚未消费变更。源库是权威状态，独立维护的投影可以暂时过期；本版建立这个可观察边界。

## Pressure / Naive / Break

- **Pressure**：读模型需要跟上源库，但消费进程可能尚未运行。
- **Naive**：分别写源库和投影，不能知道两者是否来自同一提交。
- **Break**：插入一条订单并在投影消费前读取，输出必须报告源库一行、投影零行及 `inconsistent=true`。

## Change

只冻结源库/投影分离的基线，不加入 WAL、位置或恢复机制。

## Check / Freeze

冻结 `labs/dataflows/cdc/common.py` 与 `v0.py`。独立围栏运行成功并返回不一致边界；源库的真实提交必须可查询，投影不能被脚本偷偷同步。

## Still-lacks / Next

没有变更流或 replay position，worker 崩溃会丢失交接。v1 只读取已提交 logical WAL 事件并保存单调 source position。

## Replay

```bash
uv run pytest tests/dataflows/cdc/test_e01_replay.py -q
```

外部依赖：需要 `infra/e01.compose.yaml` 提供 PostgreSQL，并设置 `E01_DATABASE_URL`。
