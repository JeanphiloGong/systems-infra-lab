# P01 v0 写作任务

外部请求是整数订单 ID 和状态字符串；保存覆盖同 ID，读取不存在返回 None，范围左闭右开。
只讨论内存数据，不声称持久性。目标文档 `tutorial.md`，代码 `labs/partitioning/routing/single.py`。

1. 场景：客服先查订单状态；给出一份字典中的 put/get，解释 None 与空字符串不同。
   checkpoint，规模 S，无前置；验收覆盖更新和缺失 ID。
2. 压力：客服需要 ID 区间的订单；原来的单键读取无法回答。
   patch，增加过滤和排序，规模 S，依赖任务 1；验收边界、乱序插入、空区间。
3. 最后呈现完整三函数检查点和断言，规模 S，依赖任务 2；在临时目录执行。
   不新增逻辑，下一版把单节点存储扩展成多个归属节点。无 helper，无提交。

不变量：保存后同键读取相同值；范围只返回符合边界的键且递增。
类型约定由调用者遵守，本版不做字符串到整数的 CLI 输入转换。


## Tutorial Increment

- **Pressure:** The tenant orders routed to shard owners scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 客服输入订单 ID 20，希望看到“已付款”。我们先把系统压缩为一份内存字典： 整数键表示订单 ID，字符串表示状态。没有网络和持久化，退出进程数据就消失。
- **Change:** # P01 v0：先让一份订单数据能够读写; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/partitioning/routing -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a P01 routing teaching model for tenant orders routed to shard owners; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of P01 routing, carrying forward the state and invariant rather than restarting from a disconnected example.

