# S01 v4 写作计划

前置 v3。目标：在不可变文件上增加可关闭的有界只读页缓存，命中改变读取次数但不能改变查询结果。

1. 从 32 次读取只有 4 个不同页出发，展示无限字典的内存问题；用容量 2 和 0,1,0,2 轨迹推导 LRU。正文“先看无限保留为什么不够”；验收明确淘汰 1 而非 0，依赖 v3，规模 S。
2. 添加 OrderedDict、容量、命中刷新与满时淘汰，计数区分逻辑请求与文件读取。完整 checkpoint 为 records.py + paged.py + workload.py；验收冷 4 次暖 0 次、工作集大于容量后重读、跨页容量 1、负容量拒绝。依赖任务 1，规模 M。
3. 重放 v0-v4 和最终测试，核对数据一致、缓存容量与 OS 缓存边界。冻结只读应用缓存，明确无更新失效/脏页/锁。依赖任务 2，规模 S。

新增抽象仅为已有 PageReader 内缓存状态，不引入包装器。容量约束只针对缓存条目和页数据，不声称全部统计内存有界。审核风险是热缓存文件变更、不正确 LRU 次序、计数把逻辑命中当成文件读取。提交策略：本轮不提交，独立审核后再决定。


## Tutorial Increment

- **Pressure:** The a file of fixed-size order records scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v3](../v3/tutorial.md)。32 条订单、64 字节一页，一共只有 4 个页；无缓存时却读取 32 次。页尺寸提供了空间局部性的机会，但只有保留已读页，后续相邻订单才可能复用它。 本篇添加只读应用缓存。文件从构造 reader 到实验结束都不可变；修改源文件后必须创建新 reader。没有脏页、写回、锁或崩溃恢复。容量以页计，保存的页面数据至多 `capacity * page_size` 字节，但 Python 字典、bytes 对象和统计集合也占内存，这不是进程内存上限。
- **Change:** # S01 v4：缓存有容量，淘汰后也要读对; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/pages -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S01 pages/locality teaching model for a file of fixed-size order records; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

