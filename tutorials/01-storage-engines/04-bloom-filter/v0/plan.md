# S04 v0 写作计划

目标：证明首个命中、最后命中、缺失键分别读取 1/3/3 个文件。前置：Python 文件读写。

场景与压缩：v0 场景是三份只读 TSV；路径顺序决定首次命中。先建立 query_files 的值/计数合同，再用空文件和缺失查询检查。未知格式和 I/O 失败不伪装为 None。

1. 先展示已有行为的成本或缺口，再解释一个新合同；正文前两段和第一小节。验收读者能指出本版需要解决什么；规模 S，依赖前置，无提交。
2. 编写完整 baseline.py 检查点，逐项解释字段和边界。验收无隐藏依赖、无未来版本机制；规模 M，依赖任务 1，代码角色 checkpoint。
3. 执行正文打印检查与独立临时目录重放；验收所有必需不变量成立，冻结本版后说明下一缺口。规模 S，依赖任务 2，无提交。

验证：首尾缺失、空列表、空文件的读取计数。风险：误把可能存在当肯定存在，误把应用读取当物理磁盘读取。


## Tutorial Increment

- **Pressure:** The negative lookups against immutable data scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 查询商品编号 missing，三个只读文件都没有它，服务却依次打开了三次文件。先别加入概率结构：我们需要一个结果正确、成本可见的基线，之后才能证明过滤器没有改变答案。 本篇把文件简化成 UTF-8 TSV，每行一对键值，用制表符分隔；键和值不含换行，键不含制表符。文件在实验期间不可变。多个文件出现相同键时以路径列表中最先找到的值为准，本文不模拟版本号或删除标记。
- **Change:** # S04 v0：不存在的键也会把每个文件读一遍; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bloom -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S04 Bloom filter teaching model for negative lookups against immutable data; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of S04 Bloom filter, carrying forward the state and invariant rather than restarting from a disconnected example.

