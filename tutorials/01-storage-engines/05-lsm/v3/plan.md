# S05 v3 计划

前置v2。任务1：从省略键导致旧值复活引出持久删除，规模S。任务2：用JSON结构化标签区分普通值与删除，规模M，不能保留任何特殊字符串。任务3：完整sstable.py与tombstones.py checkpoint，规模M；从正文提取两文件到独立目录、两个新进程create/reopen，验证删除/空串/原标记字符串/JSON形状字符串。各任务依次依赖前项，目标本目录tutorial.md对应章节，不提交Git。

值语义协议为["value", text]或["delete"]，载荷由冻结v1 SSTable保存；v3所有输入文件由TombstoneStore.create产生，不自动兼容v2原始字符串文件。调用者以新到旧列表定义优先级。测试检查更晚put覆盖旧删除、错误tag抛错和无效类型不发布文件。无合并/清单/WAL，独立review后验收。


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v2的缺失代表“继续查旧文件”。如果删除仅从新文件省略k，查询仍会从old.sst读回old。删除必须是明确命中，命中后终止搜索，才能阻止旧值复活。 先在仓库根目录将下面代码存为临时检查脚本并用 `uv run python` 执行。它只使用上一版接口，在TemporaryDirectory中展示省略键并不能删除旧值；运行后自动清理自己的目录。
- **Change:** # S05 v3：把删除作为事实保存下来; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v4 of S05 LSM/compaction, carrying forward the state and invariant rather than restarting from a disconnected example.

