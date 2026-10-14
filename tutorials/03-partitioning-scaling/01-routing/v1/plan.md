# P01 v1 写作任务

前置 v0 的单分片契约。模型：整数订单键、固定有序节点元组、稳定哈希。
输入同一键与配置必须输出相同节点；配置空或重复节点时拒绝。

1. tutorial.md 第一步：从三份订单字典提出路由需求，展示 Python 内置 hash 的跨进程种子问题。
   新增 stable_hash，解释 SHA256 前 64 位与 UTF-8/十进制键编码。规模 S，patch，依赖 v0。
   验收已知哈希向量，避免用偶然同进程结果证明跨进程一致。
2. 第二步：新增取模选择节点，完整 hashing.py checkpoint。规模 S，依赖任务 1。
   验收点查写读同路由、空节点与重复节点拒绝。
3. 第三步：相同键集从 3 节点改成 4 节点，报告移动比例并展示未搬迁造成的缺失读取。
   规模 S，实验 checkpoint，依赖任务 2；验证新旧数据物理位置不因路由函数变化而改变。

代码目标 labs/partitioning/routing/hashing.py，测试 test_p01_hashing.py。
稳定哈希是路由首次需要的 helper，只返回整数，无状态修改。
节点列表顺序是配置的一部分，集群需一致；本版不实现迁移或跨分片事务。无提交。


## Tutorial Increment

- **Pressure:** The tenant orders routed to shard owners scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** [v0](../v0/tutorial.md) 的一份字典已经能保存订单。现在准备了 a、b、c 三个节点， 每个节点各有一份字典。如果写入时随意选择节点，读取时就不得不问遍所有节点。
- **Change:** # P01 v1：用哈希给订单选择节点; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/partitioning/routing -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a P01 routing teaching model for tenant orders routed to shard owners; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of P01 routing, carrying forward the state and invariant rather than restarting from a disconnected example.

