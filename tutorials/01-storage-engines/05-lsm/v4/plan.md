# S05 v4 计划

前置v3结构化值/删除记录和v1不可变文件。场景为文件不断累积，重复值浪费查询；目标将连续区间替换为一个文件而不改变任何键读取结果。所有文件按调用者明确的新到旧优先级排列，不按mtime推断。

1. tutorial.md第一节，规模S，完整小脚本。用new里删除、old里旧值复现错误合并省略删除后的复活；读者先看到具体破坏。
2. 第二节，规模M，解释按文件优先级首次命中保留，连续[start,stop)才能用同一位置的文件替代；读取所有选中文件并验证tag，异常不发布。字典和输出排序沿用前版契约，不增加版本号。
3. 第三节，规模M，加入安全删除标记规则：stop<len(files)保留；stop==len(files)表示已覆盖全部更旧文件，可丢弃。全量是安全后缀的特例，非连续合并不在接口内。
4. 最后完整checkpoint，规模M，依赖前3项；完整打印sstable.py/tombstones.py/compaction.py，输出新文件列表但不删除输入、不发布manifest。独立目录新进程创建/重开，查询与记录内容均核对。

验证：部分合并保留delete、全合并删除delete、后缀合并不覆盖更新文件、六种连续区间全部保持读取结果、空值/特殊字符串、无效范围、坏tag、已有输出拒绝且输入不变。新进程重开与错误基线都从Markdown提取执行；不提交Git。独立review后验收。

边界：整个调用期间文件集合静止，调用者必须使用返回列表且不能随后重新加入被移除的旧文件；输入仍在磁盘用于安全回退。本版无文件清单/删除回收/WAL/并发compaction，不承诺断电恢复。S05v5才解决文件集合的原子发布。


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v3每次刷写都增加不可变文件。同一键散落多个版本，缺失查询可能扫描全部文件。现在把一组文件合并成一个，但最重要的目标是读取结果不变，而不是尽快删文件。 前置[v3](../v3/tutorial.md)。输入是静止的、新到旧排列的路径列表以及连续区间[start,stop)，输出是替换该区间后的新列表。代码不扫描目录猜版本，也不删除输入或写manifest。这里的“最新”由调用者给出的文件顺序定义。
- **Change:** # S05 v4：合并文件时，删除不能被合并掉; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v5 of S05 LSM/compaction, carrying forward the state and invariant rather than restarting from a disconnected example.

