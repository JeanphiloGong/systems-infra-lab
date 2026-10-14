# S03 v5 写作计划

前置 v4。目标是实际退出+新进程恢复，验证旧提交保留、新事务原子、已确认结果恢复和重复恢复幂等。

1. 区分 before_ack/after_ack，明确缓冲写入事件不等于 OS 持久化；推导全新与已有提交两组矩阵，并独立准备残片尾测试 tail_repaired。正文“把确认与进程存活分开观察”；验收全新10边界、已有9边界、修尾1例。依赖 v4，规模 S。
2. 新增 crash_worker CLI，在事件名匹配时 os._exit73，返回后 stdout ACK；完整 checkpoint framing.py+store.py+crash_worker.py。验收每次退出码、ACK可见性、两次独立恢复、允许旧值或完整新值。依赖任务 1，规模 M。
3. 重放全部六篇并运行行为测试，冻结有证据的进程崩溃模型，列出断电、并发、检查点与 exactly-once 边界。依赖任务 2，规模 M。

不删除单写者前提，不把模拟fsync错误称为物理断电。root目录由调用者创建，测试只用临时目录。无新兼容抽象；worker 是真实 CLI 故障入口。提交策略：本轮不提交。


## Tutorial Increment

- **Pressure:** The a confirmed order write during a process crash scenario makes the current checkpoint insufficient for the v5 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v4](../v4/tutorial.md)。轨迹说明 fsync 在确认之前，但没有真的让进程在这些位置消失。现在给每个边界一个名字，让子进程在对应探针调用 os._exit(73)，随后启动全新的 Python 进程恢复两次。 本实验覆盖程序暴露的写入、flush、fsync、数据副本与确认边界，不声称覆盖文件系统内部所有指令。帧内部每个字节的截断由 v1 测试覆盖；真实断电与设备故障仍不在测试环境内。
- **Change:** # S03 v5：在每个边界退出，再由新进程恢复; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/wal -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S03 WAL/recovery teaching model for a confirmed order write during a process crash; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

