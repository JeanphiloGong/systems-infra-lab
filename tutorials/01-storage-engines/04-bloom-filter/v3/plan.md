# S04 v3 写作计划

压力：S05 v1 每次 get 都扫描文件，即使键不存在。前置 v2 与冻结的 S05 v1 SSTable。

1. 复现独立 keys 列表漏键会导致假阴性，改为从真实 SSTable.items 构建。正文第一节，规模 S，验收文件所有键都进入过滤器。
2. 完整 checkpoint SSTable依赖、filter.py、table.py，True 继续 get、False 跳过；build_reads 和 query_reads 分开。正文第二节，规模 M，验收 bits=1 强制误报仍读取返回 None，空字符串不当缺失。
3. 用真实表和过滤表对相同 302 查询比较结果，单独输出构建扫描和查询扫描；复开仍保留全部键。正文第三节，规模 S。外部测试监测 Path.open，核对实际应用文件打开次数与统计。

不支持可变文件、持久化位数组或 tombstone 新旧优先级；未来 tombstone 键也必须进入过滤器。教程复制完整冻结依赖，不用源文件链接替代。检查点提交：本轮不提交。


## Tutorial Increment

- **Pressure:** The negative lookups against immutable data scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置是 [v2](../v2/tutorial.md) 和 S05 v1 的不可变 SSTable。本篇使用同一个 SSTable.create、items、get 实现：UTF-8 JSONL 的每行是 [字符串键,字符串值]，严格按键递增。get 目前会扫描完整文件，所以大量缺失查询仍有明显应用读取成本。 若文件里有 a、b，但调用者只提供 [a] 构建过滤器，查询 b 会被错误跳过。这是假阴性，不能用“过滤器允许误差”解释。构造器因此不接受独立键列表，而调用同一表的 items 遍历所有真实键。
- **Change:** # S04 v3：让 Bloom Filter 守在真实 SSTable 查询之前; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bloom -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S04 Bloom filter teaching model for negative lookups against immutable data; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

