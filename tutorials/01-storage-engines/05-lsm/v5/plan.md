# S05 v5 计划

前置v4文件列表/v3标签记录。目标从有效旧集合出发，发布进程异常终止后仍由新进程读取完整旧或新集合。边界为本地POSIX单写者，文件集合静止，旧文件不回收。

1. tutorial.md第一节：原地重写产生损坏JSON的可执行反例，规模S，prose+checkpoint。验收解析失败，导出完整临时写再切名要求。
2. 第二节：manifest_paths边界校验与publish同步顺序，规模M，依赖1。取basename前检查parent；拒绝重复/缺失/非.sst/符号链接；fsync数据与目录、临时manifest、replace、目录。完整本地成功边界明确，不能泛化断电证明。
3. 第三节：真正os._exit71/72故障，规模M，依赖2。预先发布old，再故障发布new，独立读进程核对值和manifest数组；不以RuntimeError代替崩溃。
4. 最后完整三个文件checkpoint，规模M，依赖3。SSTable/TombstoneStore冻结依赖全部打印，CLI --create/--publish/read分开。正文代码隔离重放实际命令序列，检查预期退出码与逻辑集合。

所有任务不提交Git。验证包括空集合、损坏JSON/名称、重复缺失文件、目录外路径、symlink、发布前后故障、新进程重开和正常发布清理。独立review后冻结，无WAL/多写者/垃圾回收。
