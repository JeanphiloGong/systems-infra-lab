# S04 v2 写作计划

目标：遍历 2×2×2 参数组合，打印理论、实测、误报分子分母和载荷字节。前置：v1。

场景与压缩：v1 只有正确性，不知道空间/误报权衡；推导独立位置近似，再解释双哈希偏差。sweep 用不重合的 present/absent 键集，不使用真实计时作设备结论。

1. 先展示已有行为的成本或缺口，再解释一个新合同；正文前两段和第一小节。验收读者能指出本版需要解决什么；规模 S，依赖前置，无提交。
2. 编写完整 filter.py + measure.py 检查点，逐项解释字段和边界。验收无隐藏依赖、无未来版本机制；规模 M，依赖任务 1，代码角色 checkpoint。
3. 执行正文打印检查与独立临时目录重放；验收所有必需不变量成立，冻结本版后说明下一缺口。规模 S，依赖任务 2，无提交。

验证：八组合、每行零假阴性、分子分母一致、显式载荷内存、零插入与非法参数。风险：误把双哈希近似当精确概率或零样本误报当零风险。


## Tutorial Increment

- **Pressure:** The negative lookups against immutable data scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v1](../v1/tutorial.md)。只测试 4096 位、5 个哈希、100 个键，不能回答“少给一半内存会怎样”或“文件增长后过滤器是否还有效”。这次保持字符串生成规则相同，遍历 m、k、n 的组合，并打印实际误报数和位数组字节数。 m 位，k 个近似均匀独立位置，插入 n 个不同键后，一位仍为零的概率约为 exp(-kn/m)。假设查询位置独立，假阳性率约为 (1-exp(-kn/m))**k。
- **Change:** # S04 v2：分别改变空间、哈希次数和插入量; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bloom -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S04 Bloom filter teaching model for negative lookups against immutable data; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of S04 Bloom filter, carrying forward the state and invariant rather than restarting from a disconnected example.

