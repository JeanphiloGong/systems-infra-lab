# P02 v1 计划

目标增加节点不能拆开单热键。使用固定输入和确定路由；每分片计数、总量守恒、热点不因扩容消失，加盐显式分担。完整checkpoint及测试；不宣称真实数据库性能。


## Tutorial Increment

- **Pressure:** The one hot tenant dominating shard traffic scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 本版使用可重复的整数请求计数模型。均匀键分布和固定hot键分布都记录每个分片请求量，不能只看平均值。加盐策略显式把子键轮转到分片，不承诺任意哈希会均匀；读取聚合必须遍历所有子键。 完整 checkpoint `labs/partitioning/skew/skew.py`：
- **Change:** # P02 v1：增加节点不能拆开单热键; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/partitioning/skew -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a P02 skew teaching model for one hot tenant dominating shard traffic; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of P02 skew, carrying forward the state and invariant rather than restarting from a disconnected example.

