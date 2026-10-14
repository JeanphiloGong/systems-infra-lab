# P01 v2 写作任务

前置 v1 的哈希路由以及它不能直接裁剪 ID 范围的限制。本版策略实验独立于 hashing.py。
模型是有序分界整数、每个区间的唯一节点、左闭右开查询。

1. 给出 `[99,101)` 对三个节点哈希路由必须散发的压力，改用分界 100、200。
   文档第一步，规模 S，patch，解释恰好等于边界的键进入右侧。
   验收 99/100/199/200 的归属。
2. 把查询边界映射为首尾区间，新增 covering；整数 stop-1 不可推广到字符串。
   文档第二步，规模 S，patch，依赖任务 1；验收空、跨界、完整范围。
3. 完整 RangeMap checkpoint；对照广播查询和裁剪查询结果一致，构造单调增长键热点。
   文档最后一步，规模 M，依赖任务 2；代码 labs/partitioning/routing/ranges.py，
   测试 test_p01_ranges.py；非法分界、节点数、重复节点明确拒绝。

RangeMap 仅保存共同使用的不可变元组配置，不隐藏存储或网络操作。
不变量为点查归属和范围裁剪不漏数据。下一版回到扩容迁移量；本版不加入在线拆分。无提交。


## Tutorial Increment

- **Pressure:** The tenant orders routed to shard owners scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** [v1](../v1/tutorial.md) 的哈希路由对点查很方便。但要查询 `[99,101)` 的全部订单， 一般无法从两个端点知道中间键属于哪些哈希分片，往往需要散发查询后合并结果。
- **Change:** # P01 v2：范围查询为什么要保留键的顺序; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/partitioning/routing -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a P01 routing teaching model for tenant orders routed to shard owners; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of P01 routing, carrying forward the state and invariant rather than restarting from a disconnected example.

