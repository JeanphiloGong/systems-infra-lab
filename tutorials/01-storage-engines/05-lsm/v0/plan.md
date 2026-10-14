# S05 v0 计划

读者会Python字典，目标实现可覆盖更新的字符串映射；场景为事件属性，压缩为单进程内存。外部输入字符串键值，缺失None、空值有效；items输出独立排序快照。

1. tutorial.md第一步展示列表保留重复键导致旧值被先找到；规模S，完整小脚本，验证具体old/new反例。
2. 第二步改为字典覆盖，items时排序；规模S，patch，验收z最后值new、a排前。明确普通dict不是平衡树，put平均O(1)、导出O(n log n)。
3. 最后给完整memtable.py checkpoint与CLI，规模M，依赖前两步；检查独立快照不受后续put改变、新实例/新进程不共享数据。下一缺口是退出丢失数据。

不新增持久化或版本序列号，无Git提交；独立review检查排序契约和复杂度边界。


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 事件处理器把z从old更新为new，查询应得到new。我们先只处理字符串键值和单进程内存，不急着写LSM目录结构。读者需要会Python字典和函数；所有命令在仓库根目录执行，先运行 `uv sync --locked`。 先运行这个完整起点：
- **Change:** # S05 v0：同一个属性更新两次，读哪一个？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of S05 LSM/compaction, carrying forward the state and invariant rather than restarting from a disconnected example.

