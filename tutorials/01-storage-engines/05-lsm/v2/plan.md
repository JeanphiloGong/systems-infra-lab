# S05 v2 计划

把v1单文件扩展为调用者按新到旧给出的文件序列。任务1：展示单文件无法同时返回新k与旧keep，规模S。任务2：逐个SSTable返回首个非None值，规模S，必须保留空字符串；列表顺序由调用者负责。任务3：完整sstable.py/versions.py checkpoint，规模M，从正文提取到临时目录独立执行两个进程create/reopen，再重放反转优先级patch。任务依次依赖前项，目标本目录tutorial.md对应章节，不提交Git。

测试跨文件同键覆盖、旧文件独有键、空值、空集合和明确反向顺序。无自动目录发现，不引入清单/合并；独立review后冻结。


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 事件属性k已经刷入old.sst，随后k更新为new。v1文件不可变，所以再次刷写要创建new.sst。只查旧文件会读到old，只查新文件又会漏掉旧文件独有的keep。目标是让多个不可变文件表现成一个最新值映射。 本版接受调用者提供的“新到旧”路径列表，不按名字或mtime猜先后，也不扫描目录。列表位置就是本版的版本优先级；重启时调用者必须提供相同顺序，文件集合的持久清单留在v5。
- **Change:** # S05 v2：多个文件里，谁是最新值？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of S05 LSM/compaction, carrying forward the state and invariant rather than restarting from a disconnected example.

