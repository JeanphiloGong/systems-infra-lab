# S02 v7 写作计划

汇总有序数组、内存 B+Tree、页编码和删除基线。用固定随机种子比较点查、范围查和插入；故障实验截断/损坏页文件，明确 v5 没有 WAL 原子性。验收参考字典一致、结构验证通过、失败边界可诊断。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v7 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 最终 checkpoint 必须组装 v6 修正后的完整 tree.py 与 v5 page_file.py，并保留数组参考。能力包括点查、闭区间扫描、页拓扑重开、局部删除重平衡和根收缩。`page_file.py` 的写入不是 WAL；进程在 `save` 中退出可能留下截断文件，CRC 和长度检查会拒绝它。 最终 checkpoint 包含下面两份完整文件，保存后即可独立运行。
- **Change:** # S02 v7：完整检查点与边界; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

