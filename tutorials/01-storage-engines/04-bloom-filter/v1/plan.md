# S04 v1 写作计划

目标：位数组的 add 不清零，因此已插入键不能出现假阴性。前置：v0。

场景与压缩：v0 显示负查询读取全部文件，精确集合可能占用大量键空间；引出位数组。先解释 1/4/7 位轨迹、假阳性碰撞，再引出稳定 UTF-8 BLAKE2b 双哈希和 bit/byte 索引。

1. 先展示已有行为的成本或缺口，再解释一个新合同；正文前两段和第一小节。验收读者能指出本版需要解决什么；规模 S，依赖前置，无提交。
2. 编写完整 filter.py 检查点，逐项解释字段和边界。验收无隐藏依赖、无未来版本机制；规模 M，依赖任务 1，代码角色 checkpoint。
3. 执行正文打印检查与独立临时目录重放；验收所有必需不变量成立，冻结本版后说明下一缺口。规模 S，依赖任务 2，无提交。

验证：所有插入键、重复插入、非法参数、强制假阳性、9 位占2字节。风险：误把可能存在当肯定存在，误把应用读取当物理磁盘读取。


## Tutorial Increment

- **Pressure:** The negative lookups against immutable data scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v0](../v0/tutorial.md)。三个文件的缺失查询都要读取。如果把文件里所有键放进精确集合，可以避免负查询，但索引的内存会随键长度增长。Bloom Filter 只保留被键设置过的位，牺牲肯定回答的精确性来压缩内存。 本篇模型只有位数组、稳定哈希位置、add 和 might_contain。没有文件查询集成，也没有删除。所有已插入键都必须返回 True；未插入键可能因为其他键的位发生碰撞而返回 True。
- **Change:** # S04 v1：用位数组给出单向可靠的否定; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bloom -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S04 Bloom filter teaching model for negative lookups against immutable data; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of S04 Bloom filter, carrying forward the state and invariant rather than restarting from a disconnected example.

