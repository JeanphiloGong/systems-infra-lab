# S01 v1 写作计划

场景和不变量继承 v0；新增合同是编号必须等于槽位，文件在查询期间不可变。目标是在任意有效位置只返回 8 字节数据。

1. 展示 `scan(path, 2) == (20, 24)`，从前一版遍历引出偏移公式。验收能计算第 2 条偏移 16；正文目标“从编号算出位置”；依赖 v0，规模 S，代码角色 patch（定位表达式）。
2. 编写直接定位函数并保留扫描对照；完整 checkpoint 目标 `records.py`。验收首尾 8 字节、负数越界零字节、乱序与截断报错。依赖任务 1，规模 S。
3. 重放正文并检查读取计数的层次；冻结直接定位版本，留下读取单位不反映页的缺口。依赖任务 2，规模 S。

本版新增 helper 是 direct，调用者为测试与后续实验，输入路径/编号，输出值和字节数，无写入。风险是误把连续编号算法称为通用索引，以及忽略并发文件修改边界。本文检查覆盖正常、缺失、损坏，不重复操作系统 open 异常测试。检查点提交：本轮不提交，独立审核后再决定。


## Tutorial Increment

- **Pressure:** The a file of fixed-size order records scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置是 [v0](../v0/tutorial.md)。最后一条订单只需返回 8 字节，扫描却把前面所有订单读了一遍。用三条记录复现：`scan(path, 2)` 返回 `(20, 24)`。这不是解码慢，而是查找路径经过了不需要的记录。 本文件的编号恰好等于从零开始的槽位，记录宽度恒为 8；因此编号 2 位于偏移 16。若只是金额字段长度固定、编号却可以乱序，这个公式便不成立。这里没有建立通用索引，连续编号是输入格式的一部分。
- **Change:** # S01 v1：利用固定记录宽度直接定位; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/pages -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S01 pages/locality teaching model for a file of fixed-size order records; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of S01 pages/locality, carrying forward the state and invariant rather than restarting from a disconnected example.

