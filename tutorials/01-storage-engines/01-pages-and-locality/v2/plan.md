# S01 v2 写作计划

目标：把 v1 的单记录读取改成按页读取，记录跨任意多个页仍正确。页长为正整数，尾页可短，文件完整且不可变；编号等于槽位。

1. 用记录 [8,16)、页长 10 展示只读起始页不足，推导末页必须使用 stop-1。正文目标“先把跨界算清楚”，验收页长 8 不多读、页长 10 跨两页；依赖 v1，规模 S，局部表达式演示。
2. 查询多个记录需要共享计数；引入 PageReader，输入路径/页长，get 输出金额或 None，read_page 返回 bytes 并更新统计。正文目标“让查询共享页尺寸与统计”，完整 checkpoint 目标 records.py + paged.py。验收所有记录值相等、短尾页、页长 1、空文件、非法页长、截断；依赖任务 1，规模 M。
3. 重放完整文件，确认 20/34 字节和 2/4 请求轨迹；冻结页读取并留下重复读取问题。依赖任务 2，规模 S。

风险：混淆完整短尾页与截断记录，混淆应用读取与磁盘 IO，将对象误讲成数据库缓冲池。提交策略：本轮不提交，独立审核并修复后再决定。


## Tutorial Increment

- **Pressure:** The a file of fixed-size order records scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v1](../v1/tutorial.md)。订单 1 的字节区间是 [8,16)。若一次读取单位为 10 字节，起始页只有区间 [0,10)，还差后面 6 字节。仅仅读取起始页再切出 8 字节会失败。这次用刻意很小的页让边界看得见，真实数据库页通常大得多。 本篇仍只读取不可变文件，编号等于槽位。页只是文件中固定大小的连续区间；最后一页允许短于页长，但文件长度必须是完整记录宽度的倍数。我们不模拟操作系统分页，也不声明一次应用页读取对应一次设备 I/O。
- **Change:** # S01 v2：读取一条跨页记录; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/pages -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S01 pages/locality teaching model for a file of fixed-size order records; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of S01 pages/locality, carrying forward the state and invariant rather than restarting from a disconnected example.

