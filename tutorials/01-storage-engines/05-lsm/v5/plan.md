# S05 v5 计划

前置v4文件列表/v3标签记录。目标从有效旧集合出发，发布进程异常终止后仍由新进程读取完整旧或新集合。边界为本地POSIX单写者，文件集合静止，旧文件不回收。

1. tutorial.md第一节：原地重写产生损坏JSON的可执行反例，规模S，prose+checkpoint。验收解析失败，导出完整临时写再切名要求。
2. 第二节：manifest_paths边界校验与publish同步顺序，规模M，依赖1。取basename前检查parent；拒绝重复/缺失/非.sst/符号链接；fsync数据与目录、临时manifest、replace、目录。完整本地成功边界明确，不能泛化断电证明。
3. 第三节：真正os._exit71/72故障，规模M，依赖2。预先发布old，再故障发布new，独立读进程核对值和manifest数组；不以RuntimeError代替崩溃。
4. 最后完整三个文件checkpoint，规模M，依赖3。SSTable/TombstoneStore冻结依赖全部打印，CLI --create/--publish/read分开。正文代码隔离重放实际命令序列，检查预期退出码与逻辑集合。

所有任务不提交Git。验证包括空集合、损坏JSON/名称、重复缺失文件、目录外路径、symlink、发布前后故障、新进程重开和正常发布清理。独立review后冻结，无WAL/多写者/垃圾回收。


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v5 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v4成功合并后返回一个新的Python文件列表，但进程退出就失去这个列表。扫描目录不能恢复它：旧输入文件仍然存在，目录中也可能有尚未发布的输出文件。我们需要一份明确记录当前读取集合的manifest，而不是根据文件名猜测。 本版限定本地POSIX文件系统、单个发布者、发布期间不修改/删除的不可变SSTable。manifest是按新到旧排列的JSON文件名数组，读取者只采用它列出的文件。数据格式沿用v3，不增加WAL或后台合并。
- **Change:** # S05 v5：重启后应该采用哪个文件集合？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v6 of S05 LSM/compaction, carrying forward the state and invariant rather than restarting from a disconnected example.

