# S05 v1 计划

前置v0。目标把排序快照保存为不可变单文件并在新进程重读。模型UTF8 JSONL行记录[key,value]；不含多文件、删除、索引或WAL。公共create接受Mapping，调用者用dict(memtable.items())刷写覆盖后最终值。

1. 第一节解释字典退出丢失，引入结构化JSON编码；规模S，示例含换行和非ASCII，验收解析不靠手工split字段。
2. 第二节定义严格排序及重复键拒绝、完整扫描读取；规模M，get不提前返回是为了检查文件尾部排序损坏。缺失None，不与空串混淆。
3. 第三节文件不可变创建；规模M，同目录临时文件完成写入flush后hard-link到目标，已有目标拒绝，finally清理临时名。解释仅POSIX本地原子命名可见性，不声称fsync崩溃持久性；文件清单仍属v5。
4. 最后完整sstable.py checkpoint与新进程create/read命令，规模M。测试排序、覆盖拒绝、无效键值、损坏形状/顺序、空表、UTF8、新进程重开。正文隔离回放不得导入当前源码。

所有任务依次依赖前项，目标同目录tutorial.md各节；不提交Git。S04集成仅依赖items/get。


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v0退出就失去所有事件属性。现在需要把一次MemTable快照写入文件，并在没有原内存对象的新进程读取。范围只有一个文件，不实现多文件优先级、删除、WAL或合并。 直接写key+"="+value会遇到键值含等号、引号或换行的歧义。本版每行用JSON数组[key,value]，文件编码UTF8。下面可独立执行的检查保留换行和非ASCII，而不是靠split猜字段：
- **Change:** # S05 v1：把排序快照刷成不可变文件; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of S05 LSM/compaction, carrying forward the state and invariant rather than restarting from a disconnected example.

