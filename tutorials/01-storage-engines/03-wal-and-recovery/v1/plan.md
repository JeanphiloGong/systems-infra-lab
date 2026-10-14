# S03 v1 写作计划

合同：encode(dict) 返回帧 bytes，decode(bytes) 返回 (完整记录, 有效前缀长度, 尾部未完成)。帧为长度、反码、JSON、CRC32；单帧最大 1 MiB。前置 v0。

1. 以第二段 JSON 半写展示边界不明确，推导长度字段和长度反码，说明 CRC 的能力边界。正文“在负载前写长度”；验收完整头损坏与尾部不完整区分。依赖 v0，规模 S。
2. 完整 checkpoint framing.py，实现 encode/decode；前者无 I/O，后者不修复文件。验收每字节截断、空输入、头与负载损坏、过大负载。依赖任务 1，规模 M。
3. 执行正文检查，冻结帧编解码，留下没有操作语义和提交规则的问题。依赖任务 2，规模 S。

不变量是解析位置只越过完整且校验通过的帧；无法可靠分类的任意介质损坏不在故障模型。提交策略：本轮不提交，独立审核后再决定。


## Tutorial Increment

- **Pressure:** The a confirmed order write during a process crash scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v0](../v0/tutorial.md)。直接覆盖丢失了操作意图，所以我们准备追加日志。但连续写入两段 JSON，进程在第二段中间退出时，读取者怎样知道第一段完整、第二段未完成？单独调用 `json.loads` 无法给整个追加文件划定事务记录边界。 本篇只实现日志帧，不承诺事务恢复或持久化。输入是字典，输出是二进制帧；解码输入完整日志 bytes，输出已完成记录、有效前缀字节数、是否存在未完成尾部。当前全量载入日志，非生产级流式解析器。
- **Change:** # S03 v1：找到日志的完整前缀; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/wal -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S03 WAL/recovery teaching model for a confirmed order write during a process crash; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of S03 WAL/recovery, carrying forward the state and invariant rather than restarting from a disconnected example.

