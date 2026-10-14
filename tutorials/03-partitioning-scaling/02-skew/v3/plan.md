# P02 v3 计划

目标观察容量与尾部延迟边界。使用固定输入和确定路由；每分片计数、总量守恒、热点不因扩容消失，加盐显式分担。完整checkpoint及测试；不宣称真实数据库性能。


## Tutorial Increment

- **Pressure:** The one hot tenant dominating shard traffic scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 本版使用可重复的离散队列模型测量固定批次的p99、每分片请求量和容量上界。均匀键分布和固定hot键分布都记录每个分片请求量；加盐显式轮转子键，共享dispatcher瓶颈会重新限制容量。 完整 checkpoint `labs/partitioning/skew/skew.py`：
- **Change:** # P02 v3：观察容量与尾部延迟边界; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/partitioning/skew -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a P02 skew teaching model for one hot tenant dominating shard traffic; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

