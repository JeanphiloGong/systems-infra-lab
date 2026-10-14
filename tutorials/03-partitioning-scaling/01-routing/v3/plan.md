# P01 v3 写作任务

前置 v1 稳定哈希和取模迁移量，v2 的范围策略权衡。输入节点集合与虚拟节点数，输出每个键的归属。
不变量：同一集合顺序无关；新增节点只接收原节点移出的键；移除节点只改变该节点原有键。

1. 从 v1 3→4 大量迁移出发，构造有序固定节点位置；查找顺时针第一个节点，末尾回绕。
   文档第一步，规模 S，独立 checkpoint；验证恰好落点和超过最大点。
2. 节点名稳定哈希映射后发现区间长度不等；每个节点加入多个虚拟点，但仍映射到物理节点。
   文档第二步，规模 S，patch；说明 JSON 编码和固定点数是配置契约。
3. 完整 HashRing 与 hashing.py checkpoint，规模 M，依赖前两步。
   文档最后一步；代码 ring.py，测试 test_p01_ring.py；检验扩缩容归属、输入边界、确定性及分布计数。

不会增加持久存储、复制或自动搬迁。owner_at 暴露哈希位置到拥有者的查询，
供 node 和环边界测试调用；无状态修改。正常键哈希冲突可同分片，节点点位冲突明确拒绝。
同一键无论请求多热仍选同一节点。全部版本独立重放后交审核，不自动提交。


## Tutorial Increment

- **Pressure:** The tenant orders routed to shard owners scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 回看 [v1](../v1/tutorial.md)：1000 个固定键从三个节点扩成四个，简单取模会改变大量归属。 如果每次扩容都搬迁大半数据，网络和磁盘会长时间忙于迁移。本篇保留稳定哈希，改变“如何选节点”。
- **Change:** # P01 v3：扩容时，只让一部分键换主人; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/partitioning/routing -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a P01 routing teaching model for tenant orders routed to shard owners; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

