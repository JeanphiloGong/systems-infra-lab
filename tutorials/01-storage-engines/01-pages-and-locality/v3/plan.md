# S01 v3 写作计划

目标：保持数据与访问集合不变，只改变排列，报告本次请求数、页请求、不同页数、读取量和逐请求延迟分位数。前置 v2；非目标是设备性能基准。

1. 展示分别随机抽样造成查询集合不同的问题；以 0..31 的排列和局部固定种子洗牌替换。正文“只改变访问顺序”；验收相同集合、可重复且未原地修改连续序列。依赖 v2，规模 S，局部演示。
2. 单次总时间看不到长尾，引出逐请求计时与 nearest-rank；测量输入为 reader/编号列表，输出整数指标字典，仅 reader 统计被读取动作修改。完整 checkpoint 是 records.py、paged.py、workload.py。验收 32 请求、4 页、2048 字节、checksum 4960、分位数排序、空输入拒绝。依赖任务 1，规模 M。
3. 重放正文并审查缓存状态描述；冻结可复现负载，下一步处理重复页读取。依赖任务 2，规模 S。

风险：checksum 不等价于逐记录验证；OS 缓存未清空；不同排列不一定产生不同应用读取次数；固定种子不代表跨所有 Python 版本稳定。提交策略：本轮不提交，独立审查后再决定。


## Tutorial Increment

- **Pressure:** The a file of fixed-size order records scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v2](../v2/tutorial.md)。现在页读取正确了，接着有人问“连续访问比随机访问快多少”。如果两次实验访问不同订单、使用不同数据规模，再各打印一次总时间，数字无法回答这个问题。 本篇比较同一集合的两种排列，固定种子，记录每次查询的延迟分布。实验不清空 OS 页缓存，不声称测出磁盘随机访问性能。生成文件本身就可能把数据留在 OS 缓存；Python 的打开文件、解释器与调度开销也包含在计时里。
- **Change:** # S01 v3：让连续与随机访问可以公平比较; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/pages -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S01 pages/locality teaching model for a file of fixed-size order records; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v4 of S01 pages/locality, carrying forward the state and invariant rather than restarting from a disconnected example.

