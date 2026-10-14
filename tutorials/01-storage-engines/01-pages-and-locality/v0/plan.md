# S01 v0 写作任务

目标是让订单查询返回值同时报告实际交给应用的字节数。约定固定 8 字节记录；输入为文件路径和整数编号，输出为 `(值或 None, 字节数)`。

1. 从三条订单中寻找最后一条开始，先展示 `struct.pack/unpack` 与二进制布局。正文目标为“先规定文件格式”；验收 3 条占 24 字节，说明小端与两个无符号整数。无依赖，规模 S，代码角色局部演示。
2. 调用者只得到订单值，看不到查询成本；给扫描增加 `consumed`，每次实际读到字节时累加。正文目标为“形成完整扫描检查点”；验收首条 8、末条 24、缺失 24，截断抛错。依赖任务 1，规模 S，代码角色 checkpoint，目标 `labs/storage/pages/records.py`。
3. 重放完整文件和检查脚本，确认空文件与不存在路径行为。冻结支持顺序扫描的版本，留下末尾查询成本随位置增长的问题。依赖任务 2，规模 S，文档目标为检查与下一步。

不变量：完整记录才解码；未找到返回 None；字节计数是应用收到的字节而不是设备读取量。计划不提交 Git；先运行检查，再独立审核。


## Tutorial Increment

- **Pressure:** The a file of fixed-size order records scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 订单导出文件里有一百万条记录。客服输入最后一条订单的编号，程序虽然只返回一个金额，却可能从文件开头读到结尾。本篇先实现正确的扫描，再把这个成本显露出来；不急着引入索引或缓存。 你需要 Python 3.12 和基本文件读写知识。在仓库根目录执行 `uv sync --group dev`。实验只创建临时文件，不需要数据库。我们把完整订单压缩成编号与金额两个整数，并假设编号从零连续排列、金额为编号乘十。真实订单可能变长、删除或乱序，这些情况不属于本格式。
- **Change:** # S01 v0：查一条订单到底读了多少字节; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/pages -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S01 pages/locality teaching model for a file of fixed-size order records; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of S01 pages/locality, carrying forward the state and invariant rather than restarting from a disconnected example.

