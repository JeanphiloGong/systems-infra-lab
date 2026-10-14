# S06 v0 写作计划

目标：行式 region 过滤求和，报告应用字节和布局字段槽位。前置 S01。输入四字段固定 56 字节，缺失地区为零填充，非缺失文本非空。

1. 用两行只查询两列引出整个行读取成本；解释 Struct 和字节宽度。正文第一节，规模 S，验收 56 字节布局。
2. 完整 rows.py 包含编码、扫描和计数，结果正确优先；正文第二节，规模 M，验收匹配/缺失/None/空文件/截断。
3. 隔离重放并冻结行基线，下一步只改变物理列布局。依赖任务2，规模 S，无提交。


## Tutorial Increment

- **Pressure:** The an order report that reads only region and amount scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 客服需要东区订单总金额。每条订单同时包含编号、地区、金额、备注，但这个查询只需要地区和金额。本篇先写一个结果正确的行式扫描器，再统计为了这两列实际读取了多少字节。 假设输入为小型不可变订单文件，无并发写入。每行使用 4 字节无符号编号、12 字节地区、8 字节无符号金额、32 字节备注，总共 56 字节。地区允许 None，编码为全零；非缺失文本不能空、含 NUL 或超过对应 UTF-8 字节宽度。备注为非空文本，金额非负。这个格式不是通用数据库类型系统。
- **Change:** # S06 v0：报表只需两列，行文件却读了四列; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/columnar -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S06 columnar storage teaching model for an order report that reads only region and amount; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of S06 columnar storage, carrying forward the state and invariant rather than restarting from a disconnected example.

